from app.models import Category, Product


def test_public_catalogue_hides_inactive_products(client, db_session):
    category = Category(name='S03 patterns')
    db_session.add(category)
    db_session.flush()
    db_session.add_all([
        Product(name='Public pattern', slug='s03-public', category_id=category.id,
                description='Stored description', material_type='Wood', is_active=True),
        Product(name='Hidden pattern', slug='s03-hidden', is_active=False),
    ])
    db_session.commit()
    response = client.get('/api/products')
    assert response.status_code == 200
    assert 's03-hidden' not in [p['slug'] for p in response.json()]
    public = next(p for p in response.json() if p['slug'] == 's03-public')
    assert public['category_name'] == 'S03 patterns'
    assert public['description'] == 'Stored description'
    assert client.get('/api/products/s03-public').json() == public
    assert client.get('/api/products/s03-hidden').status_code == 404
    assert client.get('/api/products/s03-unknown').status_code == 404
