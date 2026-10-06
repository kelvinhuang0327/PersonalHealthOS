from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import PersonProfile, User
from app.schemas.ai_modules import AIModuleEvaluationResponse, AIModuleRequest, AIModuleResponse
from app.services.ai_modules_service import run_ai_module

router = APIRouter(prefix='/ai-modules', tags=['ai-modules'])


@router.post('/health-check-interpretation', response_model=AIModuleResponse)
def health_check_interpretation(
    payload: AIModuleRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response, _evaluation = run_ai_module(
        db=db,
        user_id=str(current_user.id),
        person=target_person,
        module='health_check_interpreter',
        days=payload.days,
        focus=payload.focus,
        max_items=payload.max_items,
    )
    return response


@router.post('/symptom-analysis', response_model=AIModuleResponse)
def symptom_analysis(
    payload: AIModuleRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response, _evaluation = run_ai_module(
        db=db,
        user_id=str(current_user.id),
        person=target_person,
        module='symptom_analysis',
        days=payload.days,
        focus=payload.focus,
        max_items=payload.max_items,
    )
    return response


@router.post('/risk-prediction', response_model=AIModuleResponse)
def risk_prediction(
    payload: AIModuleRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response, _evaluation = run_ai_module(
        db=db,
        user_id=str(current_user.id),
        person=target_person,
        module='health_risk_prediction',
        days=payload.days,
        focus=payload.focus,
        max_items=payload.max_items,
    )
    return response


@router.post('/evaluate/{module_name}', response_model=AIModuleEvaluationResponse)
def evaluate_module(
    module_name: str,
    payload: AIModuleRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed_modules = {'health_check_interpreter', 'symptom_analysis', 'health_risk_prediction'}
    if module_name not in allowed_modules:
        raise HTTPException(status_code=400, detail='Unsupported module name')

    _response, evaluation = run_ai_module(
        db=db,
        user_id=str(current_user.id),
        person=target_person,
        module=module_name,
        days=payload.days,
        focus=payload.focus,
        max_items=payload.max_items,
    )
    return AIModuleEvaluationResponse(module=module_name, **evaluation)
