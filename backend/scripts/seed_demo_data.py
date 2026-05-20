from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.entities import (
    AISummary,
    HealthInsight,
    HealthMetric,
    HealthScore,
    LabReport,
    LabReportItem,
    MedicalDocument,
    PersonProfile,
    RiskAlert,
    SymptomLog,
    User,
    UserProfile,
)

DEMO_EMAIL = 'demo@health.example.com'
DEMO_PASSWORD = 'Demo1234!'


@dataclass
class DemoPersons:
    self_person: PersonProfile
    child_person: PersonProfile
    parent_person: PersonProfile


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(days: int, hour: int = 9) -> datetime:
    base = now_utc() - timedelta(days=days)
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)


def reset_demo_data(db: Session) -> None:
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user:
        db.delete(user)
        db.commit()


def create_demo_user(db: Session) -> User:
    user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), is_active=True)
    db.add(user)
    db.flush()
    db.add(
        UserProfile(
            user_id=user.id,
            full_name='健康展示帳號',
            birth_date=date(1988, 6, 12),
            gender='male',
            height_cm=Decimal('173.0'),
            weight_kg=Decimal('76.5'),
            allergies='海鮮輕微過敏',
            family_history='高血壓家族史',
            chronic_conditions='高尿酸',
        )
    )
    db.commit()
    db.refresh(user)
    return user


def create_demo_persons(db: Session, user: User) -> DemoPersons:
    self_person = PersonProfile(
        owner_user_id=user.id,
        display_name='本人',
        relationship='self',
        birth_date=date(1988, 6, 12),
        gender='male',
        height_cm=Decimal('173.0'),
        weight_kg=Decimal('76.5'),
        allergies='海鮮輕微過敏',
        family_history='高血壓家族史',
        chronic_conditions='高尿酸',
        is_default=True,
    )
    child_person = PersonProfile(
        owner_user_id=user.id,
        display_name='小孩',
        relationship='child',
        birth_date=date(2016, 5, 20),
        gender='female',
        height_cm=Decimal('126.0'),
        weight_kg=Decimal('25.8'),
        allergies='春季過敏性鼻炎',
        family_history='',
        chronic_conditions='',
        is_default=False,
    )
    parent_person = PersonProfile(
        owner_user_id=user.id,
        display_name='父母',
        relationship='parent',
        birth_date=date(1959, 9, 8),
        gender='female',
        height_cm=Decimal('158.0'),
        weight_kg=Decimal('68.4'),
        allergies='無',
        family_history='糖尿病家族史',
        chronic_conditions='高血壓',
        is_default=False,
    )
    db.add_all([self_person, child_person, parent_person])
    db.commit()
    db.refresh(self_person)
    db.refresh(child_person)
    db.refresh(parent_person)
    return DemoPersons(self_person=self_person, child_person=child_person, parent_person=parent_person)


def add_metrics(db: Session, user: User, persons: DemoPersons) -> None:
    checkpoints = [90, 82, 75, 68, 61, 54, 47, 40, 33, 26, 19, 12, 5, 2]
    for i, d in enumerate(checkpoints):
        db.add(
            HealthMetric(
                user_id=user.id,
                subject_profile_id=persons.self_person.id,
                recorded_at=days_ago(d),
                systolic_bp=126 + min(18, i),
                diastolic_bp=79 + min(10, i // 2),
                heart_rate=72 + (i % 5),
                blood_glucose=Decimal(str(95 + min(16, i))),
                weight_kg=Decimal(str(77.2 - i * 0.08)),
                sleep_hours=Decimal(str(6.4 + (i % 3) * 0.2)),
                steps=6500 + i * 180,
                note='居家量測',
                source='manual',
            )
        )
        db.add(
            HealthMetric(
                user_id=user.id,
                subject_profile_id=persons.parent_person.id,
                recorded_at=days_ago(d, hour=7),
                systolic_bp=138 + min(16, i),
                diastolic_bp=86 + min(8, i // 2),
                heart_rate=74 + (i % 4),
                blood_glucose=Decimal(str(102 + min(18, i))),
                weight_kg=Decimal(str(69.8 - i * 0.03)),
                sleep_hours=Decimal(str(6.0 + (i % 2) * 0.3)),
                steps=4200 + i * 90,
                note='晨間血壓',
                source='manual',
            )
        )

    for d in [84, 52, 21, 6]:
        db.add(
            HealthMetric(
                user_id=user.id,
                subject_profile_id=persons.child_person.id,
                recorded_at=days_ago(d, hour=18),
                heart_rate=88,
                weight_kg=Decimal('25.8'),
                sleep_hours=Decimal('8.3'),
                steps=9800,
                note='兒童活動紀錄',
                source='manual',
            )
        )

    for d, steps, sleep in [(28, 8300, Decimal('7.1')), (21, 8800, Decimal('7.4')), (14, 9200, Decimal('7.2')), (7, 9700, Decimal('7.6')), (1, 10300, Decimal('7.5'))]:
        db.add(
            HealthMetric(
                user_id=user.id,
                subject_profile_id=persons.self_person.id,
                recorded_at=days_ago(d, hour=20),
                steps=steps,
                sleep_hours=sleep,
                source='external_api',
            )
        )
    db.commit()


def add_symptoms(db: Session, user: User, persons: DemoPersons) -> None:
    rows = [
        SymptomLog(
            user_id=user.id,
            subject_profile_id=persons.self_person.id,
            symptom='腰痠',
            occurred_at=days_ago(3, hour=22),
            severity=3,
            note='久坐後加劇，伸展可緩解',
            estimated_start_date=(date.today() - timedelta(days=240)),
            estimated_duration_days=240,
            temporal_source='manual',
            confidence_score=Decimal('0.89'),
        ),
        SymptomLog(
            user_id=user.id,
            subject_profile_id=persons.self_person.id,
            symptom='疲勞',
            occurred_at=days_ago(18, hour=21),
            severity=2,
            note='近期工時長，睡眠不足',
            estimated_start_date=(date.today() - timedelta(days=35)),
            estimated_duration_days=35,
            temporal_source='manual',
            confidence_score=Decimal('0.82'),
        ),
        SymptomLog(
            user_id=user.id,
            subject_profile_id=persons.child_person.id,
            symptom='鼻塞',
            occurred_at=days_ago(12, hour=19),
            severity=1,
            note='換季輕微不適',
            estimated_start_date=(date.today() - timedelta(days=12)),
            estimated_duration_days=5,
            temporal_source='manual',
            confidence_score=Decimal('0.74'),
        ),
        SymptomLog(
            user_id=user.id,
            subject_profile_id=persons.parent_person.id,
            symptom='膝關節痠痛',
            occurred_at=days_ago(6, hour=20),
            severity=3,
            note='上下樓梯時明顯',
            estimated_start_date=(date.today() - timedelta(days=300)),
            estimated_duration_days=300,
            temporal_source='manual',
            confidence_score=Decimal('0.87'),
        ),
    ]
    db.add_all(rows)
    db.commit()


def create_document_and_report(
    db: Session,
    user: User,
    person: PersonProfile,
    filename: str,
    report_date: date,
    items: Iterable[tuple[str, Decimal, str, Decimal, Decimal, str | None]],
) -> None:
    doc = MedicalDocument(
        user_id=user.id,
        subject_profile_id=person.id,
        category='health_check',
        original_filename=filename,
        file_type='pdf',
        mime_type='application/pdf',
        file_size=2048,
        storage_bucket='local',
        storage_key=f'reports/{person.relationship}-{report_date.isoformat()}.pdf',
        parse_status='confirmed',
        confirmed_data={'reviewed': True},
        confirmed_at=days_ago(4),
        uploaded_at=days_ago(6),
    )
    db.add(doc)
    db.flush()

    report = LabReport(
        user_id=user.id,
        subject_profile_id=person.id,
        document_id=doc.id,
        report_date=report_date,
        report_type='health_check',
        raw_text='Demo lab report content',
        parser_version='demo-v1',
        created_at=days_ago(5),
    )
    db.add(report)
    db.flush()

    for idx, (name, value, unit, ref_low, ref_high, abnormal) in enumerate(items):
        db.add(
            LabReportItem(
                report_id=report.id,
                item_name=name,
                item_code=f'DEMO_{idx}',
                value_num=value,
                unit=unit,
                ref_range=f'{ref_low}-{ref_high}',
                ref_low=ref_low,
                ref_high=ref_high,
                abnormal_flag=abnormal,
                parser_confidence=Decimal('0.93'),
                captured_at=days_ago(5, hour=11),
            )
        )
    db.commit()


def add_reports(db: Session, user: User, persons: DemoPersons) -> None:
    create_document_and_report(
        db,
        user,
        persons.self_person,
        filename='self-health-check.pdf',
        report_date=date.today() - timedelta(days=22),
        items=[
            ('Uric Acid', Decimal('8.2'), 'mg/dL', Decimal('3.5'), Decimal('7.2'), 'H'),
            ('ALT', Decimal('52'), 'U/L', Decimal('0'), Decimal('40'), 'H'),
            ('LDL', Decimal('142'), 'mg/dL', Decimal('0'), Decimal('130'), 'H'),
            ('Fasting Glucose', Decimal('108'), 'mg/dL', Decimal('70'), Decimal('99'), 'H'),
        ],
    )
    create_document_and_report(
        db,
        user,
        persons.parent_person,
        filename='parent-health-check.pdf',
        report_date=date.today() - timedelta(days=30),
        items=[
            ('LDL', Decimal('165'), 'mg/dL', Decimal('0'), Decimal('130'), 'H'),
            ('Triglycerides', Decimal('220'), 'mg/dL', Decimal('0'), Decimal('150'), 'H'),
            ('Fasting Glucose', Decimal('118'), 'mg/dL', Decimal('70'), Decimal('99'), 'H'),
            ('HDL', Decimal('39'), 'mg/dL', Decimal('40'), Decimal('100'), 'L'),
        ],
    )
    create_document_and_report(
        db,
        user,
        persons.child_person,
        filename='child-school-check.pdf',
        report_date=date.today() - timedelta(days=40),
        items=[
            ('Hemoglobin', Decimal('12.8'), 'g/dL', Decimal('11.5'), Decimal('15.5'), None),
            ('WBC', Decimal('6.4'), '10^3/uL', Decimal('4.5'), Decimal('13.5'), None),
        ],
    )


def add_alerts_and_insights(db: Session, user: User, persons: DemoPersons) -> None:
    alerts = [
        RiskAlert(
            user_id=user.id,
            subject_profile_id=persons.self_person.id,
            source_type='risk_monitor',
            rule_code='BP_HIGH_3TIMES',
            risk_type='hypertension_risk',
            severity='warning',
            title='近期血壓偏高',
            message='最近三次收縮壓皆超過 140 mmHg。',
            description='建議每週固定時段量測血壓並減少鈉攝取。',
            recommendation='兩週後回看趨勢，若持續偏高請就醫。',
            status='active',
            created_at=days_ago(2),
        ),
        RiskAlert(
            user_id=user.id,
            subject_profile_id=persons.parent_person.id,
            source_type='clinical_rule',
            rule_code='METABOLIC_RISK_CLUSTER',
            risk_type='metabolic_risk',
            severity='high',
            title='代謝風險升高',
            message='血脂與血糖偏離建議範圍。',
            description='屬於代謝風險群，建議優先控制飲食與體重。',
            recommendation='與家庭醫師討論進一步治療方案。',
            status='active',
            created_at=days_ago(1),
        ),
    ]
    db.add_all(alerts)

    insights = [
        HealthInsight(
            user_id=user.id,
            subject_profile_id=persons.self_person.id,
            insight_type='trend',
            severity='warning',
            title='血壓趨勢持續上行',
            summary='近 30 天收縮壓平均上升約 8 mmHg，與睡眠下降同步。',
            recommendation='優先執行每日步行與睡眠優化計畫。',
            evidence_json={
                'rule_id': 'trend_bp_sleep_link',
                'category': 'cardio',
                'priority': 9,
                'confidence': 0.84,
                'evidence_level': 'A',
                'guideline_source': 'ACC/AHA 2017',
            },
            generated_at=days_ago(1),
            is_active=True,
        ),
        HealthInsight(
            user_id=user.id,
            subject_profile_id=persons.self_person.id,
            insight_type='lab',
            severity='warning',
            title='尿酸偏高且持續',
            summary='近兩次檢驗尿酸高於建議上限，與間歇關節不適一致。',
            recommendation='增加飲水、減少高普林食物，追蹤 4 週。',
            evidence_json={
                'rule_id': 'hyperuricemia_followup',
                'category': 'metabolic',
                'priority': 8,
                'confidence': 0.81,
                'evidence_level': 'B',
                'guideline_source': 'EULAR Gout Guideline',
            },
            generated_at=days_ago(3),
            is_active=True,
        ),
        HealthInsight(
            user_id=user.id,
            subject_profile_id=persons.parent_person.id,
            insight_type='risk',
            severity='high',
            title='父母代謝風險需要積極追蹤',
            summary='LDL、三酸甘油脂與空腹血糖均偏高，風險分層為中高。',
            recommendation='建議每週監測與每月醫療追蹤。',
            evidence_json={
                'rule_id': 'parent_metabolic_cluster',
                'category': 'clinical',
                'priority': 10,
                'confidence': 0.88,
                'evidence_level': 'A',
                'guideline_source': 'ADA + ESC Guidelines',
            },
            generated_at=days_ago(2),
            is_active=True,
        ),
    ]
    db.add_all(insights)
    db.commit()


def add_health_scores_and_summaries(db: Session, user: User, persons: DemoPersons) -> None:
    db.add_all(
        [
            HealthScore(
                user_id=user.id,
                subject_profile_id=persons.self_person.id,
                source_period_days=30,
                overall_score=72,
                cardiovascular_score=68,
                metabolic_score=70,
                weight_score=74,
                sleep_score=69,
                score_detail={'note': 'bp and uric-acid need follow-up'},
                calculated_at=days_ago(1),
            ),
            HealthScore(
                user_id=user.id,
                subject_profile_id=persons.child_person.id,
                source_period_days=30,
                overall_score=91,
                cardiovascular_score=92,
                metabolic_score=90,
                weight_score=91,
                sleep_score=92,
                score_detail={'note': 'stable child baseline'},
                calculated_at=days_ago(2),
            ),
            HealthScore(
                user_id=user.id,
                subject_profile_id=persons.parent_person.id,
                source_period_days=30,
                overall_score=63,
                cardiovascular_score=60,
                metabolic_score=58,
                weight_score=66,
                sleep_score=68,
                score_detail={'note': 'metabolic interventions recommended'},
                calculated_at=days_ago(1),
            ),
        ]
    )
    db.add_all(
        [
            AISummary(
                user_id=user.id,
                subject_profile_id=persons.self_person.id,
                period_start=date.today() - timedelta(days=30),
                period_end=date.today(),
                summary_text='血壓與尿酸為主要追蹤重點，行為改善可望在 4-8 週內見效。',
                abnormal_explanation='收縮壓與尿酸超過建議範圍。',
                recommendations='每日步行 30 分鐘、降低高普林飲食。',
                disclaimer='本平台僅提供健康管理建議，非醫療診斷。',
                model_name='health-ai-v4.5-demo',
                created_at=days_ago(1),
            ),
            AISummary(
                user_id=user.id,
                subject_profile_id=persons.parent_person.id,
                period_start=date.today() - timedelta(days=30),
                period_end=date.today(),
                summary_text='代謝指標有聚集風險，需整合飲食與藥物管理。',
                abnormal_explanation='LDL、TG、空腹血糖偏高。',
                recommendations='每週追蹤、醫師回診、強化有氧活動。',
                disclaimer='本平台僅提供健康管理建議，非醫療診斷。',
                model_name='health-ai-v4.5-demo',
                created_at=days_ago(1),
            ),
        ]
    )
    db.commit()


def ensure_upload_dirs() -> None:
    root = Path(__file__).resolve().parents[2] / 'uploads'
    (root / 'documents').mkdir(parents=True, exist_ok=True)
    (root / 'reports').mkdir(parents=True, exist_ok=True)


def run_seed(reset_first: bool) -> None:
    Base.metadata.create_all(bind=engine)
    ensure_upload_dirs()
    with SessionLocal() as db:
        if reset_first:
            reset_demo_data(db)
        user = create_demo_user(db)
        persons = create_demo_persons(db, user)
        add_metrics(db, user, persons)
        add_symptoms(db, user, persons)
        add_reports(db, user, persons)
        add_alerts_and_insights(db, user, persons)
        add_health_scores_and_summaries(db, user, persons)
        print('Demo seed completed')
        print(f'login_email={DEMO_EMAIL}')
        print(f'login_password={DEMO_PASSWORD}')
        print(f'self_person_id={persons.self_person.id}')
        print(f'child_person_id={persons.child_person.id}')
        print(f'parent_person_id={persons.parent_person.id}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Seed local demo data for Health Insights Platform')
    parser.add_argument('--reset-only', action='store_true', help='delete existing demo user/data only')
    parser.add_argument('--seed-only', action='store_true', help='seed without deleting existing demo data first')
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if args.reset_only:
            reset_demo_data(db)
            print('Demo data reset completed')
            return

    run_seed(reset_first=not args.seed_only)


if __name__ == '__main__':
    main()
