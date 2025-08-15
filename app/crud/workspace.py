# 文件: app/crud/workspace.py (最终版)

from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models
from typing import List, Optional
from ..services import stock_data
import asyncio

def get_workspace(db: Session, workspace_id: int, user_id: int) -> Optional[models.MonitorWorkspace]:
    return db.query(models.MonitorWorkspace).filter(
        models.MonitorWorkspace.id == workspace_id,
        models.MonitorWorkspace.user_id == user_id
    ).first()

def get_workspaces_by_user(db: Session, user_id: int) -> List[models.MonitorWorkspace]:
    return db.query(models.MonitorWorkspace).filter(models.MonitorWorkspace.user_id == user_id).order_by(
        models.MonitorWorkspace.id).all()

def create_workspace(db: Session, name: str, user_id: int) -> models.MonitorWorkspace:
    db_workspace = models.MonitorWorkspace(name=name, user_id=user_id)
    db.add(db_workspace)
    db.commit()
    db.refresh(db_workspace)
    return db_workspace

def update_workspace_name(db: Session, workspace_id: int, user_id: int, new_name: str) -> Optional[models.MonitorWorkspace]:
    db_workspace = get_workspace(db, workspace_id=workspace_id, user_id=user_id)
    if db_workspace:
        db_workspace.name = new_name
        db.commit()
        db.refresh(db_workspace)
    return db_workspace

def delete_workspace(db: Session, workspace_id: int, user_id: int) -> bool:
    db_workspace = get_workspace(db, workspace_id=workspace_id, user_id=user_id)
    if db_workspace:
        db.delete(db_workspace)
        db.commit()
        return True
    return False

def create_workspace_entity(
    db: Session, workspace_id: int, entity_type: str, name: str, definition: dict
) -> models.WorkspaceEntity:
    final_name = name
    final_definition = definition.copy()
    if entity_type == 'BASE':
        stock_code = final_definition.get('code')
        if not stock_code: raise ValueError("BASE 类型的实体必须在 definition 中提供 'code'")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        stock_details = loop.run_until_complete(stock_data.get_stock_details_async(stock_code))
        if stock_details:
            final_name = stock_details.get('a2', stock_code)
            final_definition['code'] = stock_details.get('a1', stock_code)
        else:
            raise ValueError(f"无法找到股票代码 '{stock_code}' 的有效信息。")
    max_order = db.query(func.max(models.WorkspaceEntity.display_order)).filter(
        models.WorkspaceEntity.workspace_id == workspace_id).scalar()
    display_order = (max_order or 0) + 1
    db_entity = models.WorkspaceEntity(
        workspace_id=workspace_id, entity_type=entity_type, name=final_name,
        definition=final_definition, display_order=display_order
    )
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    return db_entity

def update_entity_definition(
    db: Session, entity_id: int, workspace_id: int, new_name: str, new_definition: dict
) -> Optional[models.WorkspaceEntity]:
    db_entity = db.query(models.WorkspaceEntity).filter(
        models.WorkspaceEntity.id == entity_id,
        models.WorkspaceEntity.workspace_id == workspace_id
    ).first()
    if db_entity:
        db_entity.name = new_name
        db_entity.definition = new_definition
        db.commit()
        db.refresh(db_entity)
    return db_entity

def delete_entity(db: Session, entity_id: int, workspace_id: int) -> bool:
    db_entity = db.query(models.WorkspaceEntity).filter(
        models.WorkspaceEntity.id == entity_id,
        models.WorkspaceEntity.workspace_id == workspace_id
    ).first()
    if db_entity:
        db.delete(db_entity)
        db.commit()
        return True
    return False