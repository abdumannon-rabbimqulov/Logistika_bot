from fastapi import APIRouter,Depends,HTTPException,status

from config.config import get_db
from driver.crud import *

router=APIRouter(
    prefix="/driver",
    tags=["Drivers"]
)

@router.post("/truck-type-create",response_model=TruckTypeResponse,status_code=status.HTTP_201_CREATED)
async def create_truck_type(
        data:TruckTypeCreate,
        db:AsyncSession=Depends(get_db)
):
    return await create(db=db,data=data)


@router.get("/truck-type-get_all",response_model=list[TruckTypeResponse],status_code=status.HTTP_200_OK)
async def get_all_truck(
        db:AsyncSession=Depends(get_db)
):
    return await get_all(db=db)

@router.put("truck-type-update/{pk}",response_model=TruckTypeResponse,status_code=status.HTTP_200_OK)
async def truck_update(
        pk: int,
        data:TruckTypeUpdate,
        db:AsyncSession=Depends(get_db),
):
    return await update(db,pk,data)


@router.get("/get_truck_type/{pk}", response_model=TruckTypeResponse)
async def get_truck_type(pk: int, db: AsyncSession = Depends(get_db)):
    db_result = await get_one(db=db, pk=pk)
    if db_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bunday turdagi yuk mashinasi topilmadi"
        )
    return db_result



@router.delete("/delete_truck_type/{pk}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_truck_type(pk: int, db: AsyncSession = Depends(get_db)):
    success = await delete(db=db, pk=pk)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O'chirish uchun bunday turdagi yuk mashinasi topilmadi"
        )
    return None