import json
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.model_selection import train_test_split

# 自定义数据集类
class ObstetricDataset(Dataset):
    def __init__(self, questions, labels, tokenizer, max_length=128):
        self.questions = questions
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.questions)

    def __getitem__(self, idx):
        question = str(self.questions[idx])
        label = 0 if self.labels[idx] == "症状" else 1  # 将标签转换为数字

        encoding = self.tokenizer(
            question,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# 加载数据集
def load_dataset(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions = [item['question'] for item in data]
    labels = [item['label'] for item in data]
    
    return questions, labels

# 主训练函数
def train_model():
    # 模型路径
    model_name = r'D:/WORK/project2/data/models/minilm/all-MiniLM-L6-v2'
    
    # 加载分词器和模型
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
    
    # 加载数据
    questions, labels = load_dataset('D:/WORK/project2/data/prompt_datasets/obstetric_questions_cleaned.json')
    
    # 划分训练集和验证集
    train_questions, val_questions, train_labels, val_labels = train_test_split(
        questions, labels, test_size=0.2, random_state=42
    )
    
    # 创建数据集
    train_dataset = ObstetricDataset(train_questions, train_labels, tokenizer)
    val_dataset = ObstetricDataset(val_questions, val_labels, tokenizer)
    
        # 创建数据加载器
    train_dataloader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_dataloader = DataLoader(val_dataset, batch_size=16, shuffle=False)
    
    # 设置优化器和学习率调度器
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    total_steps = len(train_dataloader) * 3
    scheduler = torch.optim.lr_scheduler.LinearLR(optimizer, start_factor=1.0, end_factor=0.0, total_iters=total_steps)
    
    # 设置设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    # 训练模型
    model.train()
    for epoch in range(3):
        total_loss = 0
        for batch in train_dataloader:
            # 将数据移到设备上
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            # 前向传播
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            total_loss += loss.item()
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            scheduler.step()
        
        # 打印训练损失
        avg_train_loss = total_loss / len(train_dataloader)
        print(f"Epoch {epoch + 1}, Average Training Loss: {avg_train_loss}")
        
        # 验证模型
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for batch in val_dataloader:
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                predictions = torch.argmax(outputs.logits, dim=-1)
                
                correct += (predictions == labels).sum().item()
                total += labels.size(0)
        
        accuracy = correct / total
        print(f"Epoch {epoch + 1}, Validation Accuracy: {accuracy}")
        model.train()
    
    # 保存模型
    model.save_pretrained('./fine_tuned_model')
    tokenizer.save_pretrained('./fine_tuned_model')

if __name__ == "__main__":
    train_model()