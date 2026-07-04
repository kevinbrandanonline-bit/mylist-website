import app as app_module

app_module.app.config.update(TESTING=True, LINKBOX_DB_PATH=':memory:')
app_module.init_db(app_module.app.config['LINKBOX_DB_PATH'])

with app_module.app.test_client() as client:
    response = client.post('/linkbox/create', data={
        'title': 'Launch Page',
        'description': 'A simple launch page',
        'notes': 'Welcome',
        'link_title': 'Docs',
        'link_url': 'https://example.com',
        'theme_color': '#6d5dfc',
        'accent_color': '#4f46e5',
    }, follow_redirects=True)
    print('create_status', response.status_code)
    pages = app_module.get_linkbox_pages(app_module.app.config['LINKBOX_DB_PATH'])
    print('page_count', len(pages))
    if pages:
        page = client.get(f"/page/{pages[0]['slug']}")
        print('public_status', page.status_code)
        print('contains_title', b'Launch Page' in page.data)
