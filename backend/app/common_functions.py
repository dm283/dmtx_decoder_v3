from fastapi import status
from fastapi.exceptions import HTTPException

from endpoint_allowed_roles_dict import endpoint_allowed_roles_dict


def redefine_schema_values_to_none(data, schema_obj):
    # get data received from frontend and redefine values if value is any kind of none to None
    data_dict = data.dict()
    for k in data_dict:
        if data_dict[k] in ['null', 'undefined', '']:
            data_dict[k] = None
    return schema_obj(**data_dict)


def check_endpoint_role_access(url, type, current_role_id):
    #
    if 'ALL' in endpoint_allowed_roles_dict[type+url]:
        return

    if current_role_id not in endpoint_allowed_roles_dict[type+url]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Отсутствует доступ')
    