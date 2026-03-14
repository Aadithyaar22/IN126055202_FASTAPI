from fastapi import FastAPI, Query, Response, status, HTTPException
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()

# -----------------------
# Initial Product Data
# -----------------------
products = [
    {"id": 1, "name": "Wireless Mouse", "price": 499, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook", "price": 99, "category": "Stationery", "in_stock": True},
    {"id": 3, "name": "USB Hub", "price": 799, "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set", "price": 49, "category": "Stationery", "in_stock": True},
]

cart = []
orders = []


# -----------------------
# Helper Function
# -----------------------
def find_product(product_id: int):
    for p in products:
        if p["id"] == product_id:
            return p
    return None


def calculate_total(product, quantity):
    return product["price"] * quantity


# -----------------------
# Models
# -----------------------
class NewProduct(BaseModel):
    name: str
    price: int
    category: str
    in_stock: Optional[bool] = True


class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str


# -----------------------
# PRODUCT ENDPOINTS
# -----------------------

@app.get("/products")
def get_products():
    return {"products": products, "total": len(products)}


@app.get("/products/category/{category_name}")
def get_by_category(category_name: str):

    result = [p for p in products if p["category"] == category_name]

    if not result:
        return {"error": "No products found in this category"}

    return {"category": category_name, "products": result, "total": len(result)}


@app.get("/products/instock")
def get_instock():
    available = [p for p in products if p["in_stock"]]
    return {"in_stock_products": available, "count": len(available)}


@app.get("/products/search/{keyword}")
def search_products(keyword: str):

    results = [p for p in products if keyword.lower() in p["name"].lower()]

    if not results:
        return {"message": "No products matched your search"}

    return {"keyword": keyword, "results": results, "total_matches": len(results)}


@app.get("/store/summary")
def store_summary():

    in_stock_count = len([p for p in products if p["in_stock"]])
    out_stock_count = len(products) - in_stock_count
    categories = list(set([p["category"] for p in products]))

    return {
        "store_name": "My E-commerce Store",
        "total_products": len(products),
        "in_stock": in_stock_count,
        "out_of_stock": out_stock_count,
        "categories": categories
    }


@app.get("/products/deals")
def get_deals():

    cheapest = min(products, key=lambda p: p["price"])
    expensive = max(products, key=lambda p: p["price"])

    return {"best_deal": cheapest, "premium_pick": expensive}


@app.post("/products", status_code=201)
def add_product(new_product: NewProduct, response: Response):

    for p in products:
        if p["name"].lower() == new_product.name.lower():
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"error": "Product already exists"}

    next_id = max(p["id"] for p in products) + 1

    product = {
        "id": next_id,
        "name": new_product.name,
        "price": new_product.price,
        "category": new_product.category,
        "in_stock": new_product.in_stock
    }

    products.append(product)

    return {"message": "Product added", "product": product}


# -----------------------
# PRODUCT AUDIT
# -----------------------
@app.get("/products/audit")
def product_audit():

    in_stock_list = [p for p in products if p["in_stock"]]
    out_stock_list = [p for p in products if not p["in_stock"]]

    stock_value = sum(p["price"] * 10 for p in in_stock_list)
    priciest = max(products, key=lambda p: p["price"])

    return {
        "total_products": len(products),
        "in_stock_count": len(in_stock_list),
        "out_of_stock_names": [p["name"] for p in out_stock_list],
        "total_stock_value": stock_value,
        "most_expensive": {
            "name": priciest["name"],
            "price": priciest["price"]
        }
    }


# -----------------------
# BULK DISCOUNT
# -----------------------
@app.put("/products/discount")
def bulk_discount(
        category: str = Query(...),
        discount_percent: int = Query(..., ge=1, le=99)
):

    updated = []

    for p in products:
        if p["category"] == category:
            p["price"] = int(p["price"] * (1 - discount_percent / 100))
            updated.append(p)

    if not updated:
        return {"message": f"No products found in category: {category}"}

    return {
        "message": f"{discount_percent}% discount applied to {category}",
        "updated_count": len(updated),
        "updated_products": updated
    }


# -----------------------
# CART SYSTEM
# -----------------------

@app.post("/cart/add")
def add_to_cart(product_id: int, quantity: int = 1):

    product = find_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product["in_stock"]:
        raise HTTPException(status_code=400, detail=f"{product['name']} is out of stock")

    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            item["subtotal"] = calculate_total(product, item["quantity"])
            return {"message": "Cart updated", "cart_item": item}

    cart_item = {
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "subtotal": calculate_total(product, quantity)
    }

    cart.append(cart_item)

    return {"message": "Added to cart", "cart_item": cart_item}


@app.get("/cart")
def view_cart():

    if not cart:
        return {"message": "Cart is empty"}

    grand_total = sum(item["subtotal"] for item in cart)

    return {
        "items": cart,
        "item_count": len(cart),
        "grand_total": grand_total
    }


@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):

    for item in cart:
        if item["product_id"] == product_id:
            cart.remove(item)
            return {"message": "Item removed from cart"}

    raise HTTPException(status_code=404, detail="Item not found in cart")


@app.post("/cart/checkout")
def checkout(order: CheckoutRequest):

    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty — add items first")

    order_items = []
    grand_total = 0

    for item in cart:
        order_data = {
            "order_id": len(orders) + 1,
            "customer_name": order.customer_name,
            "product": item["product_name"],
            "quantity": item["quantity"],
            "total_price": item["subtotal"]
        }

        orders.append(order_data)
        order_items.append(order_data)
        grand_total += item["subtotal"]

    cart.clear()

    return {
        "message": "Checkout successful",
        "orders_placed": order_items,
        "grand_total": grand_total
    }


@app.get("/orders")
def get_orders():
    return {"orders": orders, "total_orders": len(orders)}


# -----------------------
# UPDATE PRODUCT
# -----------------------
@app.put("/products/{product_id}")
def update_product(
        product_id: int,
        price: Optional[int] = Query(None),
        in_stock: Optional[bool] = Query(None)
):

    product = find_product(product_id)

    if not product:
        return {"error": "Product not found"}

    if price is not None:
        product["price"] = price

    if in_stock is not None:
        product["in_stock"] = in_stock

    return {"message": "Product updated", "product": product}


# -----------------------
# DELETE PRODUCT
# -----------------------
@app.delete("/products/{product_id}")
def delete_product(product_id: int, response: Response):

    product = find_product(product_id)

    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}

    products.remove(product)

    return {"message": f"Product '{product['name']}' deleted"}


# -----------------------
# GET PRODUCT BY ID
# -----------------------
@app.get("/products/{product_id}")
def get_product(product_id: int, response: Response):

    product = find_product(product_id)

    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}

    return product