# tools/alarm.py

def should_trigger_alarm(diagnosis: dict) -> bool:
    """
    工业告警触发条件（保守策略）
    """
    if diagnosis.get("confidence", 0) < 0.7:
        return False

    for a in diagnosis.get("anomalies", []):
        if a.get("status") == "abnormal":
            return True

    return False


def trigger_alarm(diagnosis: dict):
    """
    告警动作（占位实现）
    后续可替换为 Metris / 邮件 / Teams / MES 接口
    """
    print("🚨 工业告警触发")
    print("摘要：", diagnosis.get("summary"))