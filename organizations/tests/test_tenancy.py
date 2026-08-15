import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from organizations.models import Organization, OrganizationMembership
from inventory.models import Category, Item
from pos.models import Customer, Sale


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Store A", slug="store-a")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Store B", slug="store-b")


@pytest.fixture
def user_a(org_a):
    user = User.objects.create_user(username="alice", password="pass12345")
    OrganizationMembership.objects.create(
        organization=org_a, user=user, role=OrganizationMembership.Role.OWNER
    )
    return user


@pytest.fixture
def user_b(org_b):
    user = User.objects.create_user(username="bob", password="pass12345")
    OrganizationMembership.objects.create(
        organization=org_b, user=user, role=OrganizationMembership.Role.OWNER
    )
    return user


@pytest.mark.django_db
def test_signup_creates_organization_and_owner():
    client = Client()
    response = client.post(
        reverse("organizations:signup"),
        {
            "organization_name": "Corner Shop",
            "username": "owner1",
            "email": "owner@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
        },
    )
    assert response.status_code == 302
    assert Organization.objects.filter(name="Corner Shop").exists()
    user = User.objects.get(username="owner1")
    membership = OrganizationMembership.objects.get(user=user)
    assert membership.role == OrganizationMembership.Role.OWNER
    assert membership.organization.name == "Corner Shop"


@pytest.mark.django_db
def test_login_required_redirects_anonymous():
    client = Client()
    response = client.get(reverse("pos:index"))
    assert response.status_code == 302
    assert reverse("organizations:login") in response.url


@pytest.mark.django_db
def test_users_only_see_own_organization_items(user_a, user_b, org_a, org_b):
    Item.objects.create(
        organization=org_a, name="A Item", sku="A-1", quantity=5, retail_price=10
    )
    Item.objects.create(
        organization=org_b, name="B Item", sku="B-1", quantity=8, retail_price=12
    )

    client = Client()
    client.force_login(user_a)
    response = client.get(reverse("inventory:item_list"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "A Item" in content
    assert "B Item" not in content


@pytest.mark.django_db
def test_api_isolates_categories(user_a, user_b, org_a, org_b):
    Category.objects.create(organization=org_a, name="A Cat", identifier="ACAT")
    Category.objects.create(organization=org_b, name="B Cat", identifier="BCAT")

    client = Client()
    client.force_login(user_a)
    response = client.get("/inventory/api/categories/")
    assert response.status_code == 200
    names = [row["name"] for row in response.json()["results"]]
    assert names == ["A Cat"]


@pytest.mark.django_db
def test_cannot_sell_other_org_item(user_a, org_a, org_b):
    foreign_item = Item.objects.create(
        organization=org_b, name="Foreign", sku="F-1", quantity=10, retail_price=5
    )
    client = Client()
    client.force_login(user_a)
    response = client.post(
        "/pos/api/sales/",
        {"customer": None, "items": [{"item_id": foreign_item.id, "quantity": 1}]},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert Sale.objects.count() == 0


@pytest.mark.django_db
def test_dashboard_low_stock_uses_reorder_level(user_a, org_a):
    Item.objects.create(
        organization=org_a,
        name="Milk",
        sku="M-1",
        quantity=2,
        reorder_level=5,
        retail_price=100,
    )
    Item.objects.create(
        organization=org_a,
        name="Bread",
        sku="B-1",
        quantity=20,
        reorder_level=5,
        retail_price=50,
    )
    client = Client()
    client.force_login(user_a)
    response = client.get(reverse("inventory:index"))
    assert response.status_code == 200
    assert response.context["low_stock_count"] == 1
    names = [item.name for item in response.context["low_stock_items"]]
    assert names == ["Milk"]


@pytest.mark.django_db
def test_api_ui_hidden_by_default(user_a, settings):
    settings.SHOW_API_UI = False
    client = Client()
    client.force_login(user_a)
    response = client.get(reverse("inventory:index"))
    assert b"API root" not in response.content
    response = client.get(reverse("pos:index"))
    assert b"API Root" not in response.content


@pytest.mark.django_db
def test_api_ui_shown_when_enabled(user_a, settings):
    settings.SHOW_API_UI = True
    client = Client()
    client.force_login(user_a)
    response = client.get(reverse("inventory:index"))
    assert b"API root" in response.content


@pytest.mark.django_db
def test_receipt_and_history_are_org_scoped(user_a, user_b, org_a, org_b):
    sale_a = Sale.objects.create(organization=org_a, total=10)
    sale_b = Sale.objects.create(organization=org_b, total=20)

    client = Client()
    client.force_login(user_a)
    ok = client.get(reverse("pos:receipt", args=[sale_a.id]))
    assert ok.status_code == 200
    denied = client.get(reverse("pos:receipt", args=[sale_b.id]))
    assert denied.status_code == 404

    history = client.get(reverse("pos:sale_history"))
    assert history.status_code == 200
    assert sale_a in history.context["sales"]
    assert sale_b not in history.context["sales"]


@pytest.mark.django_db
def test_customer_create_is_org_scoped(user_a, org_a):
    client = Client()
    client.force_login(user_a)
    response = client.post(
        "/pos/api/customers/",
        {"name": "Walk-in Friend", "email": "", "phone": ""},
        content_type="application/json",
    )
    assert response.status_code == 201
    customer = Customer.objects.get(name="Walk-in Friend")
    assert customer.organization_id == org_a.id
