"""
数据爬取脚本
爬取数据结构相关教育资源：
1. 教材/百科类文本（百度百科等）
2. 学术论文摘要
3. 在线课程/博客内容
"""
import re
import json
import os
import time
import hashlib
from typing import List, Dict
from urllib.parse import urljoin, quote


def clean_text(text: str) -> str:
    """清洗 HTML 标签和多余空白"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def deduplicate(items: List[Dict], key: str = 'content') -> List[Dict]:
    """基于内容哈希去重"""
    seen = set()
    result = []
    for item in items:
        h = hashlib.md5(item[key].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            result.append(item)
    return result


# ─────────────────────────────────────────────
#  百度百科爬取（数据结构相关词条）
# ─────────────────────────────────────────────
class BaiduBaikeCrawler:
    """爬取百度百科数据结构相关词条"""

    SEARCH_TERMS = [
        '数据结构', '数组', '链表', '栈', '队列', '哈希表',
        '二叉树', '二叉搜索树', 'AVL树', '红黑树', 'B树', 'B+树',
        '堆', '图', '有向图', '无向图',
        '冒泡排序', '选择排序', '插入排序', '归并排序', '快速排序', '堆排序',
        '深度优先搜索', '广度优先搜索', 'Dijkstra算法', 'Floyd算法',
        'Prim算法', 'Kruskal算法', '动态规划', '贪心算法', '分治算法',
        '递归', '哈夫曼树', '并查集', '拓扑排序',
        '二分查找', '顺序查找', '基数排序', '计数排序',
    ]

    def __init__(self, output_dir: str = '../data/raw'):
        self.output_dir = output_dir
        self.base_url = 'https://baike.baidu.com/item/'

    def crawl_single(self, term: str) -> Dict:
        """
        爬取单个词条
        注意：实际运行需安装 requests + beautifulsoup4
        此处提供完整逻辑框架，实际使用需配置网络代理
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/120.0.0.0 Safari/537.36',
            }
            encoded = quote(term)
            url = f'{self.base_url}{encoded}'
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'

            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')

            # 提取摘要
            summary_div = soup.find('div', class_='lemma-summary')
            summary = ''
            if summary_div:
                summary = clean_text(summary_div.get_text())

            # 提取正文段落
            paragraphs = []
            for p in soup.select('.para'):
                text = clean_text(p.get_text())
                if len(text) > 20:
                    paragraphs.append(text)

            content = summary + '\n\n' + '\n\n'.join(paragraphs)

            return {
                'source': url,
                'source_type': 'baike',
                'title': term,
                'content': content.strip(),
                'summary': summary,
                'crawl_time': time.strftime('%Y-%m-%d %H:%M'),
            }

        except Exception as e:
            print(f"  [错误] 爬取 '{term}' 失败: {e}")
            return None

    def crawl_all(self):
        """批量爬取所有词条"""
        print(f"[爬虫] 开始爬取 {len(self.SEARCH_TERMS)} 个百度百科词条...")
        os.makedirs(self.output_dir, exist_ok=True)

        results = []
        for i, term in enumerate(self.SEARCH_TERMS):
            print(f"  [{i+1}/{len(self.SEARCH_TERMS)}] {term}")
            data = self.crawl_single(term)
            if data and len(data['content']) > 50:
                results.append(data)
            time.sleep(1)  # 礼貌性延迟

        # 保存
        output_path = os.path.join(self.output_dir, 'baike_data.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"[爬虫] 完成！共爬取 {len(results)} 条，保存至 {output_path}")
        return results


# ─────────────────────────────────────────────
#  CSDN/博客文章爬取
# ─────────────────────────────────────────────
class BlogCrawler:
    """爬取技术博客数据结构相关文章"""

    KEYWORDS = [
        '数据结构入门', '数据结构总结', '数据结构面试题',
        '二叉树遍历', '排序算法比较', '图论算法',
        '动态规划入门', '贪心算法实例',
    ]

    def __init__(self, output_dir: str = '../data/raw'):
        self.output_dir = output_dir

    def crawl(self):
        """
        爬取 CSDN 等博客文章
        实际使用需安装 requests + beautifulsoup4
        """
        print(f"[爬虫] 开始爬取 {len(self.KEYWORDS)} 类博客文章...")
        os.makedirs(self.output_dir, exist_ok=True)

        results = []
        for kw in self.KEYWORDS:
            print(f"  搜索: {kw}")
            # 实际爬取逻辑（此处为框架）
            # url = f'https://so.csdn.net/so/search?q={quote(kw)}&t=all'
            # ... 解析搜索结果页，进入文章详情页提取内容 ...
            time.sleep(2)

        output_path = os.path.join(self.output_dir, 'blog_data.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[爬虫] 博客文章爬取完成，共 {len(results)} 条")
        return results


# ─────────────────────────────────────────────
#  数据清洗与分块（供 RAG 使用）
# ─────────────────────────────────────────────
def preprocess_data(raw_dir: str = '../data/raw',
                    output_dir: str = '../data/processed'):
    """
    对原始爬取数据进行清洗、分块
    输出：
    - cleaned_text.jsonl: 清洗后的文本块（每块 200-500 字）
    - 用于构建 FAISS 向量索引
    """
    os.makedirs(output_dir, exist_ok=True)

    all_text = []
    # 遍历所有 JSON 文件
    for fname in os.listdir(raw_dir):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(raw_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            content = item.get('content', '') or item.get('summary', '')
            if len(content) > 30:
                all_text.append({
                    'title': item.get('title', ''),
                    'content': content,
                    'source': item.get('source', ''),
                })

    # 分块（按句号分段，每块 200-500 字符）
    chunks = []
    for item in all_text:
        text = item['content']
        # 按段落分割
        paragraphs = re.split(r'[。\n]', text)
        current_chunk = f"【{item['title']}】"
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current_chunk) + len(para) > 400:
                chunks.append(current_chunk.strip())
                current_chunk = f"【{item['title']}】{para}"
            else:
                current_chunk += para + '。'
        if len(current_chunk) > 50:
            chunks.append(current_chunk.strip())

    # 去重
    unique_chunks = list(dict.fromkeys(chunks))  # 保序去重

    # 保存
    output_path = os.path.join(output_dir, 'rag_chunks.jsonl')
    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in unique_chunks:
            f.write(json.dumps({'text': chunk}, ensure_ascii=False) + '\n')

    print(f"[预处理] 完成！共生成 {len(unique_chunks)} 个文本块，保存至 {output_path}")
    return unique_chunks


# ─────────────────────────────────────────────
#  生成 NER 标注数据（半自动）
# ─────────────────────────────────────────────
def generate_ner_training_data(
    raw_dir: str = '../data/raw',
    output_dir: str = '../data/processed',
):
    """
    从清洗后的数据生成 NER 训练数据
    使用规则 + 关键词匹配进行预标注，后续人工校验
    """
    os.makedirs(output_dir, exist_ok=True)

    # 已知知识点关键词库
    entity_keywords = {
        'DS': ['数组', '链表', '单链表', '双向链表', '循环链表', '栈', '队列',
               '二叉树', '二叉搜索树', 'AVL树', '红黑树', 'B树', 'B+树', '堆',
               '图', '有向图', '无向图', '带权图', '哈希表', '哈夫曼树', '并查集',
               '完全二叉树', '满二叉树', '平衡二叉树', '线索二叉树', '线段树',
               ' Trie树', '字典树'],
        'ALGO': ['冒泡排序', '选择排序', '插入排序', '归并排序', '快速排序',
                 '堆排序', '计数排序', '基数排序', '桶排序',
                 '深度优先搜索', '广度优先搜索', 'Dijkstra算法', 'Floyd算法',
                 'Prim算法', 'Kruskal算法', '拓扑排序',
                 '前序遍历', '中序遍历', '后序遍历', '层序遍历',
                 '二分查找', '顺序查找', '哈希查找', '插值查找'],
        'CONCEPT': ['时间复杂度', '空间复杂度', '渐进分析', '最好情况', '最坏情况',
                    '平均情况', '稳定性', '原地排序', '辅助空间'],
        'METHOD': ['递归', '迭代', '分治算法', '动态规划', '贪心算法', '回溯法',
                   '分支限界法', '双指针', '滑动窗口'],
        'PRINCIPLE': ['后进先出', '先进先出', '最优子结构', '重叠子问题',
                      '贪心选择性质', '分而治之'],
    }

    # 加载清洗后的文本
    chunks_path = os.path.join(output_dir, 'rag_chunks.jsonl')
    if not os.path.exists(chunks_path):
        print("[NER] 请先运行 preprocess_data()")
        return

    ner_data = []
    with open(chunks_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            text = item['text']
            labels = []

            for etype, keywords in entity_keywords.items():
                for kw in keywords:
                    start = 0
                    while True:
                        idx = text.find(kw, start)
                        if idx == -1:
                            break
                        labels.append([idx, idx + len(kw) - 1, etype])
                        start = idx + len(kw)

            # 按 start 排序去重叠
            labels.sort(key=lambda x: x[0])
            filtered = []
            last_end = -1
            for lb in labels:
                if lb[0] > last_end:
                    filtered.append(lb)
                    last_end = lb[1]

            if filtered:
                ner_data.append({
                    'text': text,
                    'labels': filtered,
                })

    # 划分训练/开发/测试集 8:1:1
    total = len(ner_data)
    train_end = int(total * 0.8)
    dev_end = int(total * 0.9)

    splits = {
        'ner_train.jsonl': ner_data[:train_end],
        'ner_dev.jsonl': ner_data[train_end:dev_end],
        'ner_test.jsonl': ner_data[dev_end:],
    }

    for fname, data in splits.items():
        fpath = os.path.join(output_dir, fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print(f"  {fname}: {len(data)} 条")

    print(f"[NER] 共生成 {total} 条标注数据")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='数据爬取与预处理工具')
    p.add_argument('--mode', choices=['crawl', 'preprocess', 'ner'], required=True)
    p.add_argument('--raw-dir', default='../data/raw')
    p.add_argument('--out-dir', default='../data/processed')
    args = p.parse_args()

    if args.mode == 'crawl':
        crawler = BaiduBaikeCrawler(args.raw_dir)
        crawler.crawl_all()
    elif args.mode == 'preprocess':
        preprocess_data(args.raw_dir, args.out_dir)
    elif args.mode == 'ner':
        generate_ner_training_data(args.raw_dir, args.out_dir)
