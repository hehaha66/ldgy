# 文件: app/routers/workspace.py (最终版)

from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from .. import schemas, crud, models, plans
from ..database import get_db
from ..common.dependencies import get_user_from_header_or_query
from ..common.response_model import ResponseModel, APIException

router = APIRouter(
    tags=["Workspaces"],
    dependencies=[Depends(get_user_from_header_or_query)]
)

@router.post("/", response_model=ResponseModel[schemas.MonitorWorkspaceOut])
def create_new_workspace(
    workspace_in: schemas.MonitorWorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_from_header_or_query)
):
    user_plan_config = plans.PLANS_CONFIG.get(current_user.plan, plans.PLANS_CONFIG["freemium"])
    max_workspaces = user_plan_config.get('max_workspaces', 1)
    current_workspaces_count = len(crud.workspace.get_workspaces_by_user(db, user_id=current_user.id))
    if max_workspaces != -1 and current_workspaces_count >= max_workspaces:
        raise APIException(code=status.HTTP_403_FORBIDDEN, msg=f"已达到最大工作区数量限制 ({max_workspaces}个)。")
    new_workspace = crud.workspace.create_workspace(db, name=workspace_in.name, user_id=current_user.id)
    return ResponseModel(data=new_workspace)

@router.get("/", response_model=ResponseModel[List[schemas.MonitorWorkspaceOut]])
def get_user_workspaces(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_from_header_or_query)
):
    workspaces = crud.workspace.get_workspaces_by_user(db, user_id=current_user.id)
    return ResponseModel(data=workspaces)

@router.get("/{workspace_id}", response_model=ResponseModel[schemas.MonitorWorkspaceOut])
def get_single_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_from_header_or_query)
):
    workspace = crud.workspace.get_workspace(db, workspace_id=workspace_id, user_id=current_user.id)
    if not workspace:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="工作区不存在或无权访问")
    return ResponseModel(data=workspace)

@router.put("/{workspace_id}", response_model=ResponseModel[schemas.MonitorWorkspaceOut])
def rename_workspace(
    workspace_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_from_header_or_query)
):
    new_name = payload.get("name")
    if not new_name or not isinstance(new_name, str):
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="需要提供新的工作区名称 'name'")
    updated_workspace = crud.workspace.update_workspace_name(
        db, workspace_id=workspace_id, user_id=current_user.id, new_name=new_name
    )
    if not updated_workspace:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="工作区不存在或无权访问")
    return ResponseModel(data=updated_workspace)

@router.delete("/{workspace_id}", response_model=ResponseModel)
def delete_a_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_from_header_or_query)
):
    success = crud.workspace.delete_workspace(db, workspace_id=workspace_id, user_id=current_user.id)
    if not success:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="工作区不存在或无权访问")
    return ResponseModel(msg="工作区已成功删除")

@router.post("/{workspace_id}/entities", response_model=ResponseModel[schemas.WorkspaceEntityOut])
def add_entity_to_workspace(
    workspace_id: int,
    entity_in: schemas.WorkspaceEntityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_from_header_or_query)
):
    workspace = crud.workspace.get_workspace(db, workspace_id=workspace_id, user_id=current_user.id)
    if not workspace:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="工作区不存在或无权访问")
    try:
        new_entity = crud.workspace.create_workspace_entity(
            db=db,
            workspace_id=workspace_id,
            entity_type=entity_in.entity_type,
            name=entity_in.name,
            definition=entity_in.definition
        )
        return ResponseModel(data=new_entity, msg="实体添加成功")
    except ValueError as e:
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg=str(e))
    except Exception as e:
        logger.error(f"创建实体时发生数据库错误: {e}")
        raise APIException(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg="创建实体失败，请检查输入或联系管理员")

@router.put("/{workspace_id}/entities/{entity_id}", response_model=ResponseModel[schemas.WorkspaceEntityOut])
def update_workspace_entity(
    workspace_id: int,
    entity_id: int,
    entity_in: schemas.WorkspaceEntityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_from_header_or_query)
):
    workspace = crud.workspace.get_workspace(db, workspace_id=workspace_id, user_id=current_user.id)
    if not workspace:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="工作区不存在或无权访问")
    updated_entity = crud.workspace.update_entity_definition(
        db, entity_id=entity_id, workspace_id=workspace_id,
        new_name=entity_in.name, new_definition=entity_in.definition
    )
    if not updated_entity:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="实体不存在")
    return ResponseModel(data=updated_entity, msg="实体更新成功")

@router.delete("/{workspace_id}/entities/{entity_id}", response_model=ResponseModel)
def delete_entity_from_workspace(
    workspace_id: int,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_from_header_or_query)
):
    workspace = crud.workspace.get_workspace(db, workspace_id=workspace_id, user_id=current_user.id)
    if not workspace:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="工作区不存在或无权访问")
    success = crud.workspace.delete_entity(db, entity_id=entity_id, workspace_id=workspace_id)
    if not success:
        raise APIException(code=status.HTTP_404_NOT_FOUND, msg="实体不存在")
    return ResponseModel(msg="实体删除成功")