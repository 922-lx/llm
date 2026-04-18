"""
命名实体识别（NER）模型
融合多头注意力的 BERT + BiLSTM + CRF
用于从教材/论文文本中抽取知识点实体
实体类型：概念(CONCEPT)、算法(ALGO)、数据结构(DS)、原理(PRINCIPLE)、方法(METHOD)
"""
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import BertModel, BertTokenizerFast
from torchcrf import CRF
from typing import List, Dict, Tuple
import json
import os


# ─────────────────────────────────────────────
#  标签定义
# ─────────────────────────────────────────────
LABELS = [
    'O',
    'B-CONCEPT', 'I-CONCEPT',
    'B-ALGO',    'I-ALGO',
    'B-DS',      'I-DS',
    'B-PRINCIPLE','I-PRINCIPLE',
    'B-METHOD',  'I-METHOD',
]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}


# ─────────────────────────────────────────────
#  多头注意力 + BiLSTM + CRF 模型
# ─────────────────────────────────────────────
class MultiHeadAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int = 8):
        super().__init__()
        self.attn = nn.MultiheadAttention(hidden_size, num_heads, batch_first=True)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x, key_padding_mask=None):
        attn_out, _ = self.attn(x, x, x, key_padding_mask=key_padding_mask)
        return self.norm(x + attn_out)


class BertBiLSTMCRF(nn.Module):
    """
    BERT → 多头自注意力 → BiLSTM → Linear → CRF
    """
    def __init__(
        self,
        bert_name: str = 'bert-base-chinese',
        num_labels: int = len(LABELS),
        lstm_hidden: int = 256,
        num_heads: int = 8,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.bert = BertModel.from_pretrained(bert_name)
        bert_hidden = self.bert.config.hidden_size  # 768

        self.attention = MultiHeadAttention(bert_hidden, num_heads)
        self.dropout = nn.Dropout(dropout)

        self.lstm = nn.LSTM(
            input_size=bert_hidden,
            hidden_size=lstm_hidden,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout,
        )
        self.classifier = nn.Linear(lstm_hidden * 2, num_labels)
        self.crf = CRF(num_labels, batch_first=True)

    def forward(self, input_ids, attention_mask, token_type_ids=None, labels=None):
        # BERT 编码
        bert_out = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        )
        seq_out = bert_out.last_hidden_state  # (B, L, 768)

        # 多头注意力
        key_pad_mask = (attention_mask == 0)  # True 表示 padding
        seq_out = self.attention(seq_out, key_padding_mask=key_pad_mask)
        seq_out = self.dropout(seq_out)

        # BiLSTM
        lstm_out, _ = self.lstm(seq_out)  # (B, L, 512)
        lstm_out = self.dropout(lstm_out)

        # 分类
        emissions = self.classifier(lstm_out)  # (B, L, num_labels)

        if labels is not None:
            # 训练：返回 CRF loss（取负对数似然）
            mask = attention_mask.bool()
            loss = -self.crf(emissions, labels, mask=mask, reduction='mean')
            return loss
        else:
            # 推理：Viterbi 解码
            mask = attention_mask.bool()
            preds = self.crf.decode(emissions, mask=mask)
            return preds


# ─────────────────────────────────────────────
#  数据集
# ─────────────────────────────────────────────
class NERDataset(Dataset):
    """
    输入格式（JSON Lines）：
    {"text": "栈是一种后进先出的线性数据结构", "labels": [[0,1,"DS"],[3,4,"CONCEPT"],...]}
    labels: [[start_char, end_char, entity_type], ...]
    """
    def __init__(self, data_path: str, tokenizer, max_len: int = 256):
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.samples = []
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    self.samples.append(json.loads(line))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        text = sample['text']
        char_labels = ['O'] * len(text)

        for start, end, etype in sample.get('labels', []):
            if start < len(char_labels):
                char_labels[start] = f'B-{etype}'
            for i in range(start + 1, min(end + 1, len(char_labels))):
                char_labels[i] = f'I-{etype}'

        encoding = self.tokenizer(
            text,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_offsets_mapping=True,
        )

        offset_mapping = encoding['offset_mapping']
        label_ids = []
        for offset in offset_mapping:
            start, end = offset
            if start == 0 and end == 0:
                label_ids.append(LABEL2ID['O'])
            else:
                char_idx = start
                if char_idx < len(char_labels):
                    label_ids.append(LABEL2ID.get(char_labels[char_idx], 0))
                else:
                    label_ids.append(LABEL2ID['O'])

        return {
            'input_ids': torch.tensor(encoding['input_ids']),
            'attention_mask': torch.tensor(encoding['attention_mask']),
            'token_type_ids': torch.tensor(encoding.get('token_type_ids', [0] * self.max_len)),
            'labels': torch.tensor(label_ids),
        }


# ─────────────────────────────────────────────
#  训练
# ─────────────────────────────────────────────
def train(
    train_path: str,
    dev_path: str,
    save_dir: str = './models/ner',
    bert_name: str = 'bert-base-chinese',
    epochs: int = 10,
    batch_size: int = 16,
    lr: float = 2e-5,
):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'[NER] 使用设备: {device}')

    tokenizer = BertTokenizerFast.from_pretrained(bert_name)
    train_dataset = NERDataset(train_path, tokenizer)
    dev_dataset = NERDataset(dev_path, tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    dev_loader = DataLoader(dev_dataset, batch_size=batch_size)

    model = BertBiLSTMCRF(bert_name=bert_name).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.LinearLR(optimizer, total_iters=epochs * len(train_loader))

    best_f1 = 0.0
    os.makedirs(save_dir, exist_ok=True)

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            loss = model(**batch)
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        f1 = evaluate(model, dev_loader, device)
        print(f'[NER] Epoch {epoch}/{epochs} | Loss={avg_loss:.4f} | Dev F1={f1:.4f}')

        if f1 > best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), os.path.join(save_dir, 'best_model.pt'))
            tokenizer.save_pretrained(save_dir)
            print(f'[NER] 保存最佳模型（F1={best_f1:.4f}）')

    print(f'[NER] 训练完成，最佳 F1={best_f1:.4f}')


def evaluate(model, data_loader, device) -> float:
    model.eval()
    tp = fp = fn = 0
    with torch.no_grad():
        for batch in data_loader:
            labels = batch.pop('labels').cpu().tolist()
            batch = {k: v.to(device) for k, v in batch.items()}
            preds = model(**batch)
            for pred_seq, true_seq in zip(preds, labels):
                for p, t in zip(pred_seq, true_seq):
                    if p != 0 and t != 0:
                        if p == t:
                            tp += 1
                        else:
                            fp += 1
                            fn += 1
                    elif p != 0:
                        fp += 1
                    elif t != 0:
                        fn += 1
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return f1


# ─────────────────────────────────────────────
#  推理
# ─────────────────────────────────────────────
class NERPredictor:
    def __init__(self, model_dir: str, bert_name: str = 'bert-base-chinese'):
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.device = device
        self.tokenizer = BertTokenizerFast.from_pretrained(model_dir)
        self.model = BertBiLSTMCRF(bert_name=bert_name).to(device)
        self.model.load_state_dict(
            torch.load(os.path.join(model_dir, 'best_model.pt'), map_location=device)
        )
        self.model.eval()

    def predict(self, text: str) -> List[Dict]:
        """
        返回实体列表：[{'text': '栈', 'type': 'DS', 'start': 0, 'end': 1}, ...]
        """
        encoding = self.tokenizer(
            text, return_offsets_mapping=True,
            max_length=512, truncation=True,
            return_tensors='pt'
        )
        offset_mapping = encoding.pop('offset_mapping')[0].tolist()
        encoding = {k: v.to(self.device) for k, v in encoding.items()}

        with torch.no_grad():
            pred_ids = self.model(**encoding)[0]

        entities = []
        current = None
        for idx, label_id in enumerate(pred_ids):
            label = ID2LABEL.get(label_id, 'O')
            char_start, char_end = offset_mapping[idx]
            if label.startswith('B-'):
                if current:
                    entities.append(current)
                etype = label[2:]
                current = {
                    'text': text[char_start:char_end],
                    'type': etype,
                    'start': char_start,
                    'end': char_end,
                }
            elif label.startswith('I-') and current:
                current['text'] = text[current['start']:char_end]
                current['end'] = char_end
            else:
                if current:
                    entities.append(current)
                current = None
        if current:
            entities.append(current)

        return entities


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', type=str, default='../data/processed/ner_train.jsonl')
    parser.add_argument('--dev',   type=str, default='../data/processed/ner_dev.jsonl')
    parser.add_argument('--save',  type=str, default='../models/ner')
    parser.add_argument('--bert',  type=str, default='bert-base-chinese')
    parser.add_argument('--epochs', type=int, default=10)
    args = parser.parse_args()
    train(args.train, args.dev, args.save, args.bert, args.epochs)
