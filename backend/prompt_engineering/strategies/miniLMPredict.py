from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List, Tuple
import torch

class Predictor:
    def __init__(self, model_path : str) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

        self.label_map = {
            0: "symptom",
            1: "disease",
            2: "diagnosis_decision",
            3: "medical_consulation",
            4: "science_knowledge",
            5: "chat",
            6: "emotional_counseling",
            7: "life_guide",
            8: "pregnant_mother_symptom"
        }

    def predict(self, questions : List[str]) -> List[Tuple[str, float]]:
        """对多个问题进行预测"""
        # 编码问题
        encoding = self.tokenizer(
            questions,
            truncation=True,
            padding='max_length',
            max_length=128,
            return_tensors='pt'
        )

        # 将数据移到设备上
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        # 预测
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            
            # 获取预测结果
            predicted_classes = torch.argmax(logits, dim=-1).tolist()
            predicted_labels = [self.label_map[cls] for cls in predicted_classes]
            
        return predicted_labels
        

