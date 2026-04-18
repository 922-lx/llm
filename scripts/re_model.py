"""
关系抽取（RE）模型
融合 SECNN（Segment-Encoding CNN）的多层次实体关系抽取
关系类型：包含(CONTAINS)、前置(PREREQUISITE)、相关(RELATED)、
         实现(IMPLEMENTS)、对比(COMPARE)、属于(BELONGS_TO)、派生(DERIVED_FROM)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from transformers import BertModel, BertTokenizerFast
import json
import os
from typing import List, Dict, Tuple

# ─────────────────────────────────────────────
#  关系标签
# ─────────────────────────────────────────────
RELATIONS = [
    'NONE',
    'CONTAINS',       # 包含：树包含节点
    'PREREQUISITE',   # 前置：学习二叉树需要先学树
    'RELATED',        # 相关：栈与队列相关
    'IMPLEMENTS',     # 实现：快速排序实现了排序算法
    'COMPARE',        # 对比：链表与数组对比
    'BELONGS_TO',     # 属于：冒泡排序属于排序算法
    'DERIVED_FROM',   # 派生：AVL树派生自二叉搜索树
]
REL2ID = {r: i for i, r in enumerate(RELATIONS)}
ID2REL = {i: r for r, i in REL2ID.items()}
NUM_RELATIONS = len(RELATIONS)


# ─────────────────────────────────────────────
#  SECNN 模块（Segment-Encoding CNN）
# ─────────────────────────────────────────────
class SECNN(nn.Module):
    """
    对句子分段（实体前、实体间、实体后）分别卷积，增强位置感知能力
    """
    def __init__(self, input_dim: int, num_filters: int = 128, kernel_sizes: List[int] = None):
        super().__init__()
        if kernel_sizes is None:
            kernel_sizes = [2, 3, 4]
        self.convs = nn.ModuleList([
            nn.Conv1d(input_dim, num_filters, k, padding=k // 2)
            for k in kernel_sizes
        ])
        self.out_dim = num_filters * len(kernel_sizes) * 3  # 3 segments

    def forward(self, x: torch.Tensor, e1_mask: torch.Tensor, e2_mask: torch.Tensor):
        """
        x:      (B, L, H)
        e1_mask:(B, L) 实体1位置为1
        e2_mask:(B, L) 实体2位置为1
        """
        # 构建分段掩码
        B, L, H = x.shape
        x_t = x.transpose(1, 2)  # (B, H, L)

        def segment_pool(mask: torch.Tensor) -> torch.Tensor:
            """按掩码提取对应位置，做 max-over-time pooling"""
            feats = []
            for conv in self.convs:
                c = F.relu(conv(x_t))            # (B, filters, L)
                # 将 mask 广播到 filters 维，屏蔽无关位置
                m = mask.unsqueeze(1).float()    # (B, 1, L)
                c = c * m - 1e9 * (1 - m)
                pooled, _ = c.max(dim=2)         # (B, filters)
                feats.append(pooled)
            return torch.cat(feats, dim=1)       # (B, filters*len(kernels))

        # 实体1、实体2 及其余部分
        other_mask = (~(e1_mask.bool() | e2_mask.bool())).long()
        seg1 = segment_pool(e1_mask)
        seg2 = segment_pool(e2_mask)
        seg3 = segment_pool(other_mask)

        return torch.cat([seg1, seg2, seg3], dim=1)  # (B, out_dim)


# ─────────────────────────────────────────────
#  完整 RE 模型
# ─────────────────────────────────────────────
class BertSECNNRE(nn.Module):
    """
    BERT → 多头注意力 → SECNN → Dropout → Linear → Softmax
    """
    def __init__(
        self,
        bert_name: str = 'bert-base-chinese',
        num_relations: int = NUM_RELATIONS,
        num_filters: int = 128,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.bert = BertModel.from_pretrained(bert_name)
        H = self.bert.config.hidden_size  # 768

        self.attention = nn.MultiheadAttention(H, num_heads=8, batch_first=True)
        self.attn_norm = nn.LayerNorm(H)

        self.secnn = SECNN(H, num_filters=num_filters, kernel_sizes=[2, 3, 4])
        self.dropout = nn.Dropout(dropout)

        # 拼接 [CLS] + SECNN 输出
        self.classifier = nn.Sequential(
            nn.Linear(H + self.secnn.out_dim, 512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, num_relations),
        )

    def forward(self, input_ids, attention_mask, token_type_ids,
                e1_mask, e2_mask, labels=None):
        bert_out = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        )
        seq = bert_out.last_hidden_state   # (B, L, H)
        cls = bert_out.pooler_output       # (B, H)

        # 自注意力增强
        key_pad = (attention_mask == 0)
        attn_out, _ = self.attention(seq, seq, seq, key_padding_mask=key_pad)
        seq = self.attn_norm(seq + attn_out)

        # SECNN 分段特征
        secnn_out = self.secnn(seq, e1_mask, e2_mask)

        # 拼接并分类
        feat = torch.cat([cls, secnn_out], dim=1)
        feat = self.dropout(feat)
        logits = self.classifier(feat)    # (B, num_relations)

        if labels is not None:
            loss = F.cross_entropy(logits, labels)
            return loss
        return torch.argmax(logits, dim=1)


# ─────────────────────────────────────────────
#  数据集
# ─────────────────────────────────────────────
class REDataset(Dataset):
    """
    输入格式（JSON Lines）：
    {
      "text": "栈是一种线性数据结构",
      "e1": "栈", "e1_start": 0, "e1_end": 0,
      "e2": "线性数据结构", "e2_start": 4, "e2_end": 8,
      "relation": "BELONGS_TO"
    }
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
        s = self.samples[idx]
        text = s['text']
        rel = REL2ID.get(s.get('relation', 'NONE'), 0)

        encoding = self.tokenizer(
            text, max_length=self.max_len,
            padding='max_length', truncation=True,
            return_offsets_mapping=True,
        )
        offsets = encoding['offset_mapping']
        L = len(offsets)

        e1_mask = [0] * L
        e2_mask = [0] * L
        for i, (st, en) in enumerate(offsets):
            if st == 0 and en == 0:
                continue
            if s['e1_start'] <= st <= s['e1_end']:
                e1_mask[i] = 1
            if s['e2_start'] <= st <= s['e2_end']:
                e2_mask[i] = 1

        return {
            'input_ids':      torch.tensor(encoding['input_ids']),
            'attention_mask': torch.tensor(encoding['attention_mask']),
            'token_type_ids': torch.tensor(encoding.get('token_type_ids', [0] * L)),
            'e1_mask':        torch.tensor(e1_mask),
            'e2_mask':        torch.tensor(e2_mask),
            'labels':         torch.tensor(rel),
        }


# ─────────────────────────────────────────────
#  训练 & 评估
# ─────────────────────────────────────────────
def train(
    train_path: str,
    dev_path: str,
    save_dir: str = './models/re',
    bert_name: str = 'bert-base-chinese',
    epochs: int = 10,
    batch_size: int = 16,
    lr: float = 2e-5,
):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'[RE] 使用设备: {device}')

    tokenizer = BertTokenizerFast.from_pretrained(bert_name)
    train_ds = REDataset(train_path, tokenizer)
    dev_ds   = REDataset(dev_path, tokenizer)
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    dev_dl   = DataLoader(dev_ds,   batch_size=batch_size)

    model = BertSECNNRE(bert_name=bert_name).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    os.makedirs(save_dir, exist_ok=True)

    best_acc = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_dl:
            batch = {k: v.to(device) for k, v in batch.items()}
            loss = model(**batch)
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()

        acc = evaluate(model, dev_dl, device)
        print(f'[RE] Epoch {epoch}/{epochs} | Loss={total_loss/len(train_dl):.4f} | Acc={acc:.4f}')

        if acc > best_acc:
            best_acc = acc
            torch.save(model.state_dict(), os.path.join(save_dir, 'best_model.pt'))
            tokenizer.save_pretrained(save_dir)
            print(f'[RE] 保存最佳模型 Acc={best_acc:.4f}')

    print(f'[RE] 训练完成，最佳准确率={best_acc:.4f}')


def evaluate(model, data_loader, device) -> float:
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for batch in data_loader:
            labels = batch.pop('labels').to(device)
            batch = {k: v.to(device) for k, v in batch.items()}
            preds = model(**batch)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    return correct / total if total > 0 else 0.0


# ─────────────────────────────────────────────
#  推理
# ─────────────────────────────────────────────
class REPredictor:
    def __init__(self, model_dir: str, bert_name: str = 'bert-base-chinese'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = BertTokenizerFast.from_pretrained(model_dir)
        self.model = BertSECNNRE(bert_name=bert_name).to(self.device)
        self.model.load_state_dict(
            torch.load(os.path.join(model_dir, 'best_model.pt'), map_location=self.device)
        )
        self.model.eval()

    def predict(self, text: str, e1: str, e1_start: int, e1_end: int,
                e2: str, e2_start: int, e2_end: int) -> str:
        sample = {
            'text': text, 'e1': e1, 'e1_start': e1_start, 'e1_end': e1_end,
            'e2': e2, 'e2_start': e2_start, 'e2_end': e2_end, 'relation': 'NONE',
        }
        ds = REDataset.__new__(REDataset)
        ds.tokenizer = self.tokenizer
        ds.max_len = 256
        ds.samples = [sample]
        item = ds[0]
        batch = {k: v.unsqueeze(0).to(self.device) for k, v in item.items() if k != 'labels'}
        with torch.no_grad():
            pred = self.model(**batch)
        return ID2REL.get(pred.item(), 'NONE')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--train', default='../data/processed/re_train.jsonl')
    p.add_argument('--dev',   default='../data/processed/re_dev.jsonl')
    p.add_argument('--save',  default='../models/re')
    p.add_argument('--bert',  default='bert-base-chinese')
    p.add_argument('--epochs', type=int, default=10)
    args = p.parse_args()
    train(args.train, args.dev, args.save, args.bert, args.epochs)
