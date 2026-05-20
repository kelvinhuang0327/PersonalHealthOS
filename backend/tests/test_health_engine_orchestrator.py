import asyncio
from types import SimpleNamespace

from app.services.health_ai_engine.orchestrator import HealthEngineOrchestrator


class DummyPerson(SimpleNamespace):
    pass


def test_orchestrator_run_handles_failed_stage_and_continues():
    orchestrator = HealthEngineOrchestrator(db=None, person=DummyPerson(id='p1'))

    orchestrator._clinical_scores_engine = lambda context: {'ok': True}

    def fail_anomaly(context):
        raise RuntimeError('boom')

    orchestrator._anomaly_engine = fail_anomaly
    orchestrator._risk_engine = lambda context: {'risk_level': 'medium'}
    orchestrator._insight_engine = lambda context: ['i1']
    orchestrator._recommendation_engine = lambda context: ['r1']
    orchestrator._narrative_engine = lambda context: {'summary': 'fine'}

    result = asyncio.run(orchestrator.run_full_analysis({'user_id': 'u1', 'person_id': 'p1'}))

    assert result.clinical_scores == {'ok': True}
    assert result.anomalies is None
    assert result.risk_level == {'risk_level': 'medium'}
    assert result.insights == ['i1']
    assert result.recommendations == ['r1']
    assert result.narrative == {'summary': 'fine'}


def test_orchestrator_run_supports_async_engine_functions():
    orchestrator = HealthEngineOrchestrator(db=None, person=DummyPerson(id='p1'))

    async def async_scores(context):
        return {'async': True}

    orchestrator._clinical_scores_engine = async_scores
    orchestrator._anomaly_engine = lambda context: []
    orchestrator._risk_engine = lambda context: {'risk_level': 'low'}
    orchestrator._insight_engine = lambda context: []
    orchestrator._recommendation_engine = lambda context: []
    orchestrator._narrative_engine = lambda context: {'summary': 'ok'}

    result = asyncio.run(orchestrator.run_full_analysis({'user_id': 'u1', 'person_id': 'p1'}))

    assert result.clinical_scores == {'async': True}
    assert result.narrative == {'summary': 'ok'}


def test_orchestrator_run_recovers_when_narrative_fails():
    orchestrator = HealthEngineOrchestrator(db=None, person=DummyPerson(id='p1'))

    orchestrator._clinical_scores_engine = lambda context: {'ok': True}
    orchestrator._anomaly_engine = lambda context: []
    orchestrator._risk_engine = lambda context: {'risk_level': 'low'}
    orchestrator._insight_engine = lambda context: ['i1']
    orchestrator._recommendation_engine = lambda context: ['r1']

    def fail_narrative(context):
        raise ValueError('narrative failed')

    orchestrator._narrative_engine = fail_narrative

    result = asyncio.run(orchestrator.run_full_analysis({'user_id': 'u1', 'person_id': 'p1'}))

    assert result.recommendations == ['r1']
    assert result.narrative is None
