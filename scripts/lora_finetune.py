"""
LoRA 微调脚本
基于 Qwen2.5-7B-Instruct，使用 LoRA 进行参数高效微调
数据集：《数据结构》课程问答对
"""
import json
import os
import torch
from typing import List, Dict
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType
from trl import SFTTrainer


# ─────────────────────────────────────────────
#  数据加载
# ─────────────────────────────────────────────
def load_qa_dataset(data_path: str) -> List[Dict]:
    """
    加载问答数据集
    格式（JSON Lines）：
    {"instruction": "什么是二叉搜索树？", "output": "二叉搜索树（BST）是一种..."}
    """
    samples = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def format_instruction(sample: Dict) -> str:
    """格式化为 ChatML 模板"""
    system = "你是数据结构课程的专业助教，请准确、清晰地回答学生的问题。"
    user = sample.get('instruction', '')
    assistant = sample.get('output', '')
    return f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n{assistant}<|im_end|>"


# ─────────────────────────────────────────────
#  微调主函数
# ─────────────────────────────────────────────
def finetune(
    data_path: str,
    output_dir: str = './models/qwen2.5-7b-ds-lora',
    base_model: str = 'Qwen/Qwen2.5-7B-Instruct',
    num_epochs: int = 3,
    batch_size: int = 4,
    grad_accum: int = 4,
    learning_rate: float = 2e-4,
    max_seq_len: int = 1024,
    use_4bit: bool = True,
    lora_rank: int = 64,
    lora_alpha: int = 128,
    lora_dropout: float = 0.05,
    test_size: float = 0.1,
):
    """
    LoRA 微调流程：
    1. 加载基座模型（可选 4-bit 量化）
    2. 配置 LoRA 适配器
    3. 加载 & 格式化数据集
    4. 使用 trl SFTTrainer 训练
    5. 保存 LoRA 权重
    """
    print(f"[LoRA] 基座模型: {base_model}")
    print(f"[LoRA] 数据路径: {data_path}")
    print(f"[LoRA] 输出目录: {output_dir}")

    # ── Step 1: 加载 Tokenizer ──
    tokenizer = AutoTokenizer.from_pretrained(
        base_model,
        trust_remote_code=True,
        padding_side='right',
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── Step 2: 加载模型（4-bit 量化节省显存）──
    bnb_config = None
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type='nf4',
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map='auto',
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    model.config.use_cache = False

    if use_4bit:
        model = prepare_model_for_kbit_training(model)

    # ── Step 3: 配置 LoRA ──
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=[
            'q_proj', 'k_proj', 'v_proj', 'o_proj',
            'gate_proj', 'up_proj', 'down_proj',
        ],
        bias='none',
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── Step 4: 加载数据 ──
    raw_data = load_qa_dataset(data_path)
    print(f"[LoRA] 加载 {len(raw_data)} 条问答对")

    # 划分训练集/验证集
    split_idx = int(len(raw_data) * (1 - test_size))
    train_data = raw_data[:split_idx]
    val_data = raw_data[split_idx:]

    train_dataset = Dataset.from_list([
        {'text': format_instruction(s)} for s in train_data
    ])
    val_dataset = Dataset.from_list([
        {'text': format_instruction(s)} for s in val_data
    ])

    print(f"[LoRA] 训练集: {len(train_dataset)} 条 | 验证集: {len(val_dataset)} 条")

    # ── Step 5: 训练参数 ──
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=learning_rate,
        lr_scheduler_type='cosine',
        warmup_ratio=0.1,
        logging_steps=10,
        save_strategy='epoch',
        eval_strategy='epoch',
        bf16=True,
        optim='paged_adamw_8bit',
        max_grad_norm=1.0,
        report_to='none',
    )

    # ── Step 6: 训练 ──
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        args=training_args,
        dataset_text_field='text',
        max_seq_length=max_seq_len,
        packing=True,
    )

    print("[LoRA] 开始训练...")
    trainer.train()

    # ── Step 7: 保存 ──
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # 保存训练配置
    config = {
        'base_model': base_model,
        'lora_rank': lora_rank,
        'lora_alpha': lora_alpha,
        'epochs': num_epochs,
        'train_size': len(train_dataset),
        'val_size': len(val_dataset),
    }
    with open(os.path.join(output_dir, 'finetune_config.json'), 'w') as f:
        json.dump(config, f, indent=2)

    print(f"[LoRA] 模型保存至: {output_dir}")
    print("[LoRA] 训练完成！")


# ─────────────────────────────────────────────
#  推理测试
# ─────────────────────────────────────────────
def test_inference(
    lora_path: str = './models/qwen2.5-7b-ds-lora',
    base_model: str = 'Qwen/Qwen2.5-7B-Instruct',
    question: str = '什么是快速排序？请详细说明其原理。',
):
    """加载微调后的模型进行推理测试"""
    import torch

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map='auto',
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, lora_path)
    model.eval()

    system = "你是数据结构课程的专业助教，请准确、清晰地回答学生的问题。"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors='pt').to(model.device)

    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.7, do_sample=True)

    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    print(f"\n问题: {question}")
    print(f"回答: {response}\n")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')

    # 训练
    t = sub.add_parser('train')
    t.add_argument('--data', default='../data/processed/qa_train.jsonl')
    t.add_argument('--output', default='../models/qwen2.5-7b-ds-lora')
    t.add_argument('--base', default='Qwen/Qwen2.5-7B-Instruct')
    t.add_argument('--epochs', type=int, default=3)
    t.add_argument('--rank', type=int, default=64)
    t.add_argument('--no-4bit', action='store_true')

    # 测试推理
    test = sub.add_parser('test')
    test.add_argument('--lora', default='../models/qwen2.5-7b-ds-lora')
    test.add_argument('--base', default='Qwen/Qwen2.5-7B-Instruct')
    test.add_argument('--question', default='什么是快速排序？')

    args = p.parse_args()

    if args.cmd == 'train':
        finetune(
            data_path=args.data,
            output_dir=args.output,
            base_model=args.base,
            num_epochs=args.epochs,
            lora_rank=args.rank,
            use_4bit=not args.no_4bit,
        )
    elif args.cmd == 'test':
        test_inference(args.lora, args.base, args.question)
    else:
        p.print_help()
