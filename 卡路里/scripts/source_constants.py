"""body_composition source 字段的共享常量

V1.0 §02 第 ⑧ 反模式"魔法字符串"消除:所有 source 字面量集中在此。
"""
SOURCE_HOME_CALIPER = 'home_caliper'
SOURCE_HOSPITAL = 'hospital'
SOURCE_CHOICES = (SOURCE_HOME_CALIPER, SOURCE_HOSPITAL)
SOURCE_LABELS = {
    SOURCE_HOME_CALIPER: '家测皮褶钳',
    SOURCE_HOSPITAL: '医院测',
}
