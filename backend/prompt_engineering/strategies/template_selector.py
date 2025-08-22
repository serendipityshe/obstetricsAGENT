import os
from re import template
from unicodedata import category 
import yaml
from typing import Dict, Any
from .miniLMPredict import Predictor

class TemplateSelector:
    def __init__(self, template_root : str = '/root/project2/backend/prompt_engineering/templates'):

        self.template_root = template_root
        self.predictor = Predictor('/root/project2/data/models/minilm/allminilm_L6_v2_class9')

        self.label_mapping = {
            0: 'symptom',
            1: 'disease',
            2: 'diagnosis_decision',
            3: 'medical_consulation',
            4: 'science_knowledge',
            5: 'chat',
            6: 'emotional_counseling',
            7: 'life_guide',
            8: 'pregnant_mother_symptom'
        }

    def _load_template(self, template_path : str) -> Dict[str, Any]:
        """加载yaml格式的提示词模板"""
        try:
            with open(template_path, 'r', encoding= 'utf-8') as f:
                template = yaml.safe_load(f)
            return template
        except FileNotFoundError:
            default_path = os.path.join(self.template_root, 'default.yaml')
            with open(default_path, 'r', encoding= 'utf-8') as f:
                template = yaml.safe_load(f)
            return template


    def _classify_query(self, query : str) -> str:
        """根据用户问题分类"""
        label = self.predictor.predict([query])[0]
        return label

    def select_template(self, user_type : str, query : str) -> Dict[str, Any]:
        """根据用户类型和查询内容选择合适模板"""
        if user_type != 'doctor':
            category = self._classify_query(query)
            template_path = os.path.join(self.template_root, f'pregnant_mother/{category}.yaml')
            print(template_path)

        else:
            category = self._classify_query(query)
            template_path = os.path.join(self.template_root, f'doctor/{category}.yaml')
            print(template_path)

        return self._load_template(template_path)