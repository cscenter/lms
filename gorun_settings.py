DIRECTORIES = [
    ('cscsite/' + name +'/',
     'python cscsite/manage.py test ' + name + ' --settings=cscsite.settings.test')
    for name in ['users', 'core', 'learning']
]
