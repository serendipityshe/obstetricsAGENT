
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

import yaml
from typing import Annotated, Optional, List, TypedDict, Dict, Any
from langgraph.graph import StateGraph, END, START
from backend.agents.tools.tools import qwen_tool
from backend.prompt_engineering.strategies.template_selector import TemplateSelector

class GenSynthAgentState(TypedDict):
    """
    生成合成智能体
    """
    input: Annotated[str, "用户输入"]
    user_type: Annotated[str, "用户类型"]
    output: Annotated[str, "生成结果"]
    context: Annotated[str, "上下文"]
    error: Annotated[Optional[str], "错误信息"]


# 新增：流式版本的生成合成节点
async def gen_synth_node_stream(state: GenSynthAgentState):
    """
    流式生成合成智能体节点
    实时yield AI生成的每个token
    """
    try:
        user_type = state['user_type']
        template_selector = TemplateSelector()
        template_dict = template_selector.select_template(query=state['input'], user_type=user_type)
        template = template_dict['messages'][0]['content']
        system_message = template.format(query=state["input"], context=state["context"])

        with open("backend/config/model_settings.yaml", "r", encoding="utf-8") as f:
            model_settings = yaml.safe_load(f)
        default_model_config = model_settings.get("DEFAULT_MODEL")

        # 引入流式工具
        from backend.agents.tools.tools import qwen_tool_stream

        # 流式调用AI模型
        async for chunk in qwen_tool_stream(
            input=system_message,
            img_path='',
            model_name=default_model_config["llm_model"],
            api_key=default_model_config["api_key"],
            base_url=default_model_config["base_url"],
            temperature=default_model_config["temperature"]
        ):
            # 实时yield每个chunk给上层
            yield chunk

    except Exception as e:
        yield f"\n\n❌ 生成失败：{str(e)}"

def gen_synth_node(state: GenSynthAgentState) -> GenSynthAgentState:
    """
    生成合成智能体节点
    """
    try:
        user_type = state['user_type']
        template_selector = TemplateSelector()
        template_dict = template_selector.select_template(query=state['input'], user_type=user_type)
        template = template_dict['messages'][0]['content']
        system_message = template.format(query = state["input"], context = state["context"])

        with open("backend/config/model_settings.yaml", "r", encoding="utf-8") as f:
            model_settings = yaml.safe_load(f)
        default_model_config = model_settings.get("DEFAULT_MODEL")
        qwen_result = qwen_tool.invoke({
            "input": system_message,
            "img_path": '',  
            "model_name": default_model_config["llm_model"],
            "api_key": default_model_config["api_key"],
            "base_url": default_model_config["base_url"],
            "temperature": default_model_config["temperature"]
        })
        state["output"] = qwen_result['content']
        state['error'] = None
    except Exception as e:
        state['output'] = None
        state['error'] = f"生成失败：{str(e)}"
    return state

def gen_synth_agent():
    """
    生成合成智能体
    """
    builder = StateGraph(GenSynthAgentState)
    builder.add_node("gen_synth_node", gen_synth_node)
    builder.add_edge(START, "gen_synth_node")
    builder.add_edge("gen_synth_node", END)
    return builder.compile()

if __name__ == '__main__':
    agent = gen_synth_agent()
    state = {
        "user_type": "pregnant_mother",
        "input": "孕妇如何预防感冒",
        "context": "对于非特应性患者急性细菌性鼻窦炎的症状缓解，抗组胺药没有作用[19]。也无使用减充血剂或愈创甘油醚获益的有力证据。(参见 “妊娠期过敏性疾病的识别与处理”，关于‘糖皮质激素鼻喷雾剂’一节)\\n有关无并发症的细菌性鼻-鼻窦炎患者的监测和随访，详见其他专题。(参见 “成人单纯性急性鼻窦炎和鼻-鼻窦炎的治疗”)\\n流感\\n临床表现和诊断 — 流感病毒在社区活跃时，如果患者突然出现发热、咳嗽和肌痛，则应疑诊流感。其他症状也常见，如不适、咽痛、恶心、鼻塞和头痛。流感病毒检测结果阳性即确诊流感；但结果阴性并不能排除感染，尤其是所用检测的敏感性不足，或在发病后超过4日采集样本时。\\n1918年、1957年和2009年流感大流行期间，妊娠期患者的并发症发生率和死亡率增加。晚期妊娠阶段孕产妇死亡风险似乎最高，但由于妊娠相关的Th1免疫减弱，任何妊娠阶段发生的流感都可能严重。此外，甲型流感病毒可穿过胎盘[23]。妊娠期流感病毒感染可能严重，且免疫接种很安全，因此，美国妇产科医师学会(American College of Obstetricians and Gynecologists, ACOG)和美国CDC推荐孕妇在整个妊娠期普遍接种疫苗。(参见 “妊娠期免疫接种”，关于‘流感灭活疫苗’一节)\\n治疗\\n●抗病毒治疗–对于疑似急性流感的妊娠期及产后2周内患者，无论疫苗接种状态如何，都推荐及时启动恰当的经验性抗流感病毒药物治疗，例如奥司他韦口服75mg、一日2次，连用5日。与一般人群相比，妊娠期及近期妊娠的患者住院、入住ICU和死亡的风险都更高。虽然出现症状后48小时内开始抗病毒治疗的益处最大，但对于症状发作后超过48小时才就诊的患者，尤其是临床情况尚未改善者，仍需给予抗病毒治疗。妊娠期流感的诊断、临床病程、急性期治疗和预防详见其他专题。(参见 “季节性流感和妊娠”)\\n呼吸道合胞病毒与妊娠 — 由于年幼儿童相对常见RSV感染，家中有年幼儿童的孕妇感染RSV的风险可能较高。 \\n临床表现和诊断 — 大多数有症状成人在感染后3-5日出现上呼吸道感染表现，例如鼻塞、鼻溢和咽痛。 部分患者进展为下呼吸道感染，出现咳嗽、喘息和呼吸困难等症状。 还有一些患者会出现严重疾病，例如肺炎、呼吸衰竭和/或急性心脏事件。 若要进行诊断性检查，首选逆转录PCR。(参见 “成人呼吸道合胞病毒感染”，关于‘临床表现’一节和 “成人呼吸道合胞病毒感染”，关于‘诊断’一节)\\n治疗 — 大多数患者采用支持治疗。(参见 “成人呼吸道合胞病毒感染”，关于‘治疗’一节)\\n妊娠期的影响和疫苗接种 — 一些研究评估了妊娠期感染RSV的影响。  \\n●一篇系统评价纳入11项研究、超过8000例孕妇，发现汇总RSV感染率为26/1000人年[24]。 无死亡病例。 对比RSV阳性与阴性孕妇的研究发现，自然流产、死产或低出生体重的风险无差异，但感染增加了早产。\\n●一项关于RSV住院监测网络数据的研究报道，在COVID大流行前因RSV感染住院的18-49岁患者中，妊娠并不是出现严重不良结局(如入住ICU、院内死亡)的危险因素[25]。 \\n然而，一项连续横断面研究利用医疗保健成本和利用项目的全国住院患者样本，评估了16,000多例分娩时已诊断为RSV感染的患者，发现这些患者的早产风险增加，母亲短期并发症(如肺部并发症)发生率也增加[26]。 RSV感染者也更有可能存在哮喘、糖尿病合并妊娠以及孕前高血压。\\n妊娠32-37周时可选择接种RSV疫苗，为新生儿提供被动保护。 相关资料和备选方案详见其他专题(参见 “妊娠期免疫接种”，关于‘呼吸道合胞病毒疫苗’一节)。 接种RSV疫苗对母亲也有益，但50岁以下非妊娠者无需接种。(参见 “成人呼吸道合胞病毒感染”，关于‘疫苗接种’一节) \\n社区获得性肺炎\\n临床表现和诊断 — 社区获得性肺炎(community-acquired pneumonia, CAP)的典型症状是突发寒战，随后出现发热、胸膜炎性胸痛、呼吸急促和咳脓痰，但大多数患者并无典型症状。妊娠期患者CAP的临床表现和妊娠期疑似CAP患者的诊断性评估，与非妊娠期患者类似。(参见 “成人社区获得性肺炎概述”，关于‘临床表现’一节和 “成人社区获得性肺炎概述”，关于‘诊断’一节)\\n诊断CAP需拍摄胸片，疑诊CAP的妊娠期患者必须行此检查。妊娠期患者拍摄胸片(后前位和侧位)的指征与非妊娠期患者相同，包括呼吸急促和/或咳嗽伴发热、心动过速、呼吸过速、血氧饱和度降低、或肺部检查时发现啰音或肺实变征象。估计胎儿因拍摄胸片吸收的辐射量<0.01mGy(<0.001rad)，远低于引起任何近期或远期不良反应的剂量[27]。应遮蔽患者腹部。(参见 “妊娠期和哺乳期患者的诊断性影像学检查”)'}, {'source': 'data\\\\raw_manuals\\\\new_data.json', 'priority': None, 'content': '驱虫剂的使用 — 美国CDC建议孕妇采取防护措施，通过穿戴防护服(包括经扑灭司林处理的防护服)和使用含N,N-二乙基-3-甲基苯甲酰胺(N,N-diethyl-3-methylbenzamide, DEET)的驱虫剂来避免蚊虫叮咬，从而降低感染虫媒病毒的风险，如寨卡病毒、西尼罗病毒和疟疾[63]。无论孕龄如何，局部涂抹DEET都不会危害发育中的胎儿。(参见 “防止节肢动物叮咬的 驱虫剂和其他措施”，关于‘经扑灭司林处理的衣物’一节)\\n妊娠纹和其他皮肤、指甲、毛发的正常变化 — 妊娠期皮肤的正常生理变化见附表 (表 13)。 虽然妊娠纹会在产后逐渐消退，但不会完全消失，且无有效的预防或治疗方法。(参见 “妊娠期母亲皮肤和相关结构的适应性变化”)\\n纹身和人体穿孔 — 孕妇应避免在妊娠期纹身，但如果在不知晓怀孕的情况下纹身，也可安慰患者尚未证实纹身对妊娠有风险。孕妇的口鼻呼吸道、乳头、肚脐和生殖器穿孔均有风险；可能需取下这些部位的首饰，以方便临产、分娩和母乳喂养。(参见 “妊娠期母亲皮肤和相关结构的适应性变化”，关于‘纹身和穿孔’一节)\\n常见不适的处理\\n恶心和呕吐 — 几乎所有孕妇都在妊娠较早期出现恶心伴或不伴呕吐，少数人极其严重，称为妊娠剧吐。分阶段采取行为改变和药物对大部分孕妇有效 (流程图 3)。(参见 “妊娠期恶心和呕吐的临床表现与评估”和 “妊娠期恶心和呕吐的治疗和结局”)\\n胃食管反流病 — 40%-85%的孕妇会出现胃食管反流病(gastroesophageal reflux disease, GERD)。初始处理包括改变生活方式和饮食，如抬高床头、避免膳食诱发物。若孕妇的症状持续，应首选抗酸剂、藻酸盐或硫糖铝药物治疗。若治疗无效，应与非妊娠患者类似，使用H2受体拮抗剂(histamine 2 receptor antagonist, H2RA)，随后使用质子泵抑制剂(proton pump inhibitor, PPI)来控制症状 (表 14)。 应避免使用伏诺拉生(Vonoprazan)，因为尚缺乏人类妊娠中使用该药的重大先天异常、流产或其他不良母胎结局风险的相关信息。 (参见 “成人胃食管反流病的初始治疗”，关于‘妊娠期或哺乳期患者’一节)\\n便秘 — 每个妊娠阶段和产后6-12周，便秘发生率介于16%-39%。由于激素因素(如，孕激素会减慢胃肠道运动)和机械因素(如，妊娠子宫对结肠的压力)，便秘在妊娠期较常见。产前维生素中的铁、身体活动减少和其他因素可能也有一定作用。\\n首选增加膳食纤维和液体摄入，或使用膨胀性轻泻药，因为这些物质/药物不会被吸收。对于难治性病例，偶尔使用氢氧化镁、乳果糖、比沙可啶或聚乙二醇很可能没有害处，因为镁盐广泛用于妊娠期，安全性良好，而乳果糖、比沙可啶和聚乙二醇虽然尚未在人类妊娠中充分研究，但吸收量极小[64]。蓖麻油能刺激子宫收缩，过多使用矿物油可干扰脂溶性维生素的吸收，通常都应避免使用。(参见 “成人慢性便秘的治疗”)\\n痔疮 — 30%-40%的孕产妇存在痔疮相关不适。妊娠期间以保守治疗为主，重点是改变饮食和生活方式，以及使用温和的轻泻药和大便软化剂以避免便秘。(参见 “妊娠期胃肠道适应性变化”，关于‘痔’一节和 “症状性痔的家庭和门诊治疗”)\\n鼻充血和鼻出血\\n●鼻充血–20%-30%的孕妇在妊娠期间会出现有症状的鼻充血，称为妊娠期鼻炎，由激素介导且无明确的过敏性原因。妊娠期鼻炎会在产后2周内完全消退，无需治疗，药物也无充分作用。(参见 “鼻炎概述”，关于‘妊娠期鼻炎’一节)\\n变应性鼻炎通常之前就存在，但也可能在妊娠期间发生或首次被发现。这些患者常诉有严重的打喷嚏、鼻痒和水样鼻溢，部分还并发眼部瘙痒和刺激(过敏性结膜炎)。治疗方法见流程图 (流程图 4)，详见其他专题。(参见 “妊娠期过敏性疾病的识别与处理”，关于‘过敏性鼻炎/结膜炎’一节)\\n●鼻出血–孕妇也常发生鼻出血，这可能由激素介导的鼻黏膜充血导致。处理与非妊娠人群相同。(参见 “成人鼻出血的处理方法”)\\n牙龈炎 — 大多数孕妇出现牙龈变化和/或牙龈炎 (图片 1)。这些变化包括牙间乳头的增大和变钝，这可能导致牙龈出血、溃疡形成和疼痛。除了良好的口腔卫生以外，治疗妊娠性牙龈炎还需要清创和可能需要使用辅助抗生素。(参见 “成人牙龈炎和牙周炎概述”，关于‘非菌斑相关性牙龈炎和牙龈病’一节)'}, {'source': 'data\\\\raw_manuals\\\\new_data.json', 'priority': None, 'content': '对于妊娠期普通感冒患者，可告知其症状通常会在10日内消退，但咳嗽可能持续更长时间。药物治疗可能缓解一些症状，但不会缩短症状的持续时间；尚无随机试验研究妊娠期普通感冒药物治疗的风险。",
    }
    result = agent.invoke(state)
    print(result["output"])


