from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_active_year, get_db
from app.models.academic_year import AcademicYear
from app.models.record import Record
from app.schemas.record import RecordCreate, RecordOut, RecordSortUpdate, RecordUpdate

router = APIRouter(prefix="/records", tags=["records"])


@router.get("", response_model=list[RecordOut])
def list_records(
    db: Session = Depends(get_db),
    year: AcademicYear = Depends(get_active_year),
):
    """获取当前学年的所有记录，按sort_order排序"""
    records = (
        db.query(Record)
        .filter(Record.academic_year_id == year.id)
        .order_by(Record.sort_order, Record.id)
        .all()
    )
    return records


@router.post("", response_model=RecordOut, status_code=201)
def create_record(
    payload: RecordCreate,
    db: Session = Depends(get_db),
    year: AcademicYear = Depends(get_active_year),
):
    """新增项目"""
    # 检查是否已存在
    existing = (
        db.query(Record)
        .filter(
            Record.academic_year_id == year.id,
            Record.event_name == payload.event_name,
            Record.group_name == payload.group_name,
            Record.gender == payload.gender,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="该项目已存在")

    # 获取当前最大排序号
    max_sort = (
        db.query(Record.sort_order)
        .filter(Record.academic_year_id == year.id)
        .order_by(Record.sort_order.desc())
        .first()
    )
    next_sort = (max_sort[0] + 1) if max_sort else 0

    # 创建记录
    record = Record(
        academic_year_id=year.id,
        event_name=payload.event_name,
        group_name=payload.group_name,
        gender=payload.gender,
        sort_order=next_sort,
        holder_name="",
        result="",
        current_holder_name="",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record


@router.put("/{record_id}", response_model=RecordOut)
def update_record(
    record_id: int,
    payload: RecordUpdate,
    db: Session = Depends(get_db),
):
    """更新记录的姓名、成绩、历史成绩、当前成绩创造者"""
    record = db.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    record.holder_name = payload.holder_name
    record.result = payload.result
    record.current_holder_name = payload.current_holder_name
    record.historical_result = payload.historical_result
    db.commit()
    db.refresh(record)
    return record


@router.put("/sort", response_model=dict)
def update_sort(
    payload: RecordSortUpdate,
    db: Session = Depends(get_db),
):
    """批量更新排序"""
    for item in payload.updates:
        record_id = item.get("id")
        sort_order = item.get("sort_order")
        if record_id is not None and sort_order is not None:
            record = db.get(Record, record_id)
            if record:
                record.sort_order = sort_order
    db.commit()
    return {"message": "排序更新成功"}


@router.delete("/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
):
    """删除记录"""
    record = db.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    db.delete(record)
    db.commit()
    return None
