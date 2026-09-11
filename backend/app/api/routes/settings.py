"""系统设置 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.setting import AppSetting
from app.schemas.setting import SettingOut, SettingUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db)):
    """获取所有系统设置"""
    settings = db.query(AppSetting).all()
    return settings


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    payload: SettingUpdate,
    db: Session = Depends(get_db),
):
    """更新或创建系统设置"""
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting:
        setting.value = payload.value
    else:
        setting = AppSetting(key=key, value=payload.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
