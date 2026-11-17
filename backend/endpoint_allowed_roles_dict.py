endpoint_allowed_roles_dict = {
    'put'+'upload_file': ['admin',],
    'put'+'/upload_excel_list/': ['admin',],
    'put'+'/upload_file_for_carpass/': ['ALL', ],
    'get'+'log_records': ['admin',],
    'get'+'tcell': ['admin', 'dispatcher'],
    'get'+'download_carpass': ['admin', 'dispatcher'],
    'get'+'download-file-by-filename': ['admin', 'dispatcher'],
    'post'+'create_related_docs_record': ['admin', 'dispatcher', 'checkpoint', 'client', 'broker',],
    'get'+'download-file': ['admin', 'dispatcher', 'checkpoint', 'client','broker'],
    'get'+'obj_docs': ['admin', 'dispatcher', 'checkpoint', 'client', 'broker'],

    # users
    'get'+'users': [1,],
    'get'+'user': [1,0],
    # user card
    'post'+'users': [1,],
    'put'+'users': [1,],
    'get'+'user_by_uuid': [1,],

    # tasks
    'get'+'user_tasks': [1,0],

    # delete items
    'delete'+'users': [1,],

}
