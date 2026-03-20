from fastapi import FastAPI, Query, Response
from pydantic import BaseModel, Field
from typing import Optional
import math

app = FastAPI()

# -------------------- Q1 --------------------
@app.get("/")
def home():
    return {"message": "Welcome to CineStar Booking"}


# -------------------- Q2 --------------------
movies = [
    {"id": 1, "title": "Inception", "genre": "Sci-Fi", "language": "English", "duration_mins": 148, "ticket_price": 200, "seats_available": 50},
    {"id": 2, "title": "KGF", "genre": "Action", "language": "Kannada", "duration_mins": 160, "ticket_price": 180, "seats_available": 40},
    {"id": 3, "title": "RRR", "genre": "Action", "language": "Telugu", "duration_mins": 180, "ticket_price": 220, "seats_available": 30},
    {"id": 4, "title": "Interstellar", "genre": "Sci-Fi", "language": "English", "duration_mins": 169, "ticket_price": 250, "seats_available": 25},
    {"id": 5, "title": "Joker", "genre": "Drama", "language": "English", "duration_mins": 122, "ticket_price": 150, "seats_available": 35},
    {"id": 6, "title": "3 Idiots", "genre": "Comedy", "language": "Hindi", "duration_mins": 170, "ticket_price": 140, "seats_available": 60},
]

@app.get("/movies")
def get_movies():
    total_seats = sum(m["seats_available"] for m in movies)
    return {"movies": movies, "total": len(movies), "total_seats_available": total_seats}


# -------------------- Q5 (placed before /{id}) --------------------
@app.get("/movies/summary")
def summary():
    prices = [m["ticket_price"] for m in movies]
    genres = {}

    for m in movies:
        genres[m["genre"]] = genres.get(m["genre"], 0) + 1

    return {
        "total_movies": len(movies),
        "most_expensive": max(prices),
        "cheapest": min(prices),
        "total_seats": sum(m["seats_available"] for m in movies),
        "genre_count": genres
    }




# -------------------- Q4 --------------------
bookings = []
booking_counter = 1

@app.get("/bookings")
def get_bookings():
    total_revenue = sum(b["total_cost"] for b in bookings)
    return {"bookings": bookings, "total": len(bookings), "total_revenue": total_revenue}


# -------------------- Q6 --------------------
class BookingRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    movie_id: int = Field(..., gt=0)
    seats: int = Field(..., gt=0, le=10)
    phone: str = Field(..., min_length=10)
    seat_type: str = "standard"
    promo_code: str = ""


# -------------------- Q7 --------------------
def find_movie(movie_id):
    for m in movies:
        if m["id"] == movie_id:
            return m
    return None


def calculate_cost(price, seats, seat_type, promo):
    multiplier = 1
    if seat_type == "premium":
        multiplier = 1.5
    elif seat_type == "recliner":
        multiplier = 2

    total = price * seats * multiplier

    discount = 0
    if promo == "SAVE10":
        discount = total * 0.1
    elif promo == "SAVE20":
        discount = total * 0.2

    return total, total - discount


# -------------------- Q8 --------------------
@app.post("/bookings")
def create_booking(req: BookingRequest):
    global booking_counter

    movie = find_movie(req.movie_id)
    if not movie:
        return {"error": "Movie not found"}

    if movie["seats_available"] < req.seats:
        return {"error": "Not enough seats"}

    original, final = calculate_cost(
        movie["ticket_price"], req.seats, req.seat_type, req.promo_code
    )

    movie["seats_available"] -= req.seats

    booking = {
        "booking_id": booking_counter,
        "customer_name": req.customer_name,
        "movie": movie["title"],
        "seats": req.seats,
        "seat_type": req.seat_type,
        "original_cost": original,
        "total_cost": final
    }

    bookings.append(booking)
    booking_counter += 1

    return booking


# -------------------- Q10 --------------------
@app.get("/movies/filter")
def filter_movies(
    genre: Optional[str] = None,
    language: Optional[str] = None,
    max_price: Optional[int] = None
):
    result = movies

    if genre is not None:
        result = [m for m in result if m["genre"] == genre]

    if language is not None:
        result = [m for m in result if m["language"] == language]

    if max_price is not None:
        result = [m for m in result if m["ticket_price"] <= max_price]

    return {"movies": result, "count": len(result)}
# -------------------- Q3 --------------------

# -------------------- Q11 --------------------
class NewMovie(BaseModel):
    title: str
    genre: str
    language: str
    duration_mins: int
    ticket_price: int
    seats_available: int


@app.post("/movies")
def add_movie(movie: NewMovie, response: Response):
    for m in movies:
        if m["title"].lower() == movie.title.lower():
            return {"error": "Duplicate movie"}

    new = movie.dict()
    new["id"] = len(movies) + 1
    movies.append(new)

    response.status_code = 201
    return new


# -------------------- Q12 --------------------
@app.put("/movies/{movie_id}")
def update_movie(movie_id: int, ticket_price: Optional[int] = None, seats_available: Optional[int] = None):
    movie = find_movie(movie_id)
    if not movie:
        return {"error": "Not found"}

    if ticket_price is not None:
        movie["ticket_price"] = ticket_price
    if seats_available is not None:
        movie["seats_available"] = seats_available

    return movie


# -------------------- Q13 --------------------
@app.delete("/movies/{movie_id}")
def delete_movie(movie_id: int):
    movie = find_movie(movie_id)
    if not movie:
        return {"error": "Not found"}

    for b in bookings:
        if b["movie"] == movie["title"]:
            return {"error": "Cannot delete movie with bookings"}

    movies.remove(movie)
    return {"message": "Deleted"}


# -------------------- Q14 --------------------
holds = []
hold_counter = 1

class HoldRequest(BaseModel):
    customer_name: str
    movie_id: int
    seats: int


@app.post("/seat-hold")
def hold_seat(req: HoldRequest):
    global hold_counter

    movie = find_movie(req.movie_id)
    if not movie or movie["seats_available"] < req.seats:
        return {"error": "Not available"}

    movie["seats_available"] -= req.seats

    hold = {
        "hold_id": hold_counter,
        "customer": req.customer_name,
        "movie_id": req.movie_id,
        "seats": req.seats
    }

    holds.append(hold)
    hold_counter += 1
    return hold


@app.get("/seat-hold")
def get_holds():
    return holds


# -------------------- Q15 --------------------
@app.post("/seat-confirm/{hold_id}")
def confirm_hold(hold_id: int):
    global booking_counter

    for h in holds:
        if h["hold_id"] == hold_id:
            movie = find_movie(h["movie_id"])

            booking = {
                "booking_id": booking_counter,
                "customer_name": h["customer"],
                "movie": movie["title"],
                "seats": h["seats"],
                "total_cost": movie["ticket_price"] * h["seats"]
            }

            bookings.append(booking)
            booking_counter += 1
            holds.remove(h)

            return booking

    return {"error": "Hold not found"}


@app.delete("/seat-release/{hold_id}")
def release_hold(hold_id: int):
    for h in holds:
        if h["hold_id"] == hold_id:
            movie = find_movie(h["movie_id"])
            movie["seats_available"] += h["seats"]
            holds.remove(h)
            return {"message": "Released"}

    return {"error": "Not found"}


# -------------------- Q16 --------------------
@app.get("/movies/search")
def search_movies(keyword: str):
    result = [
        m for m in movies
        if keyword.lower() in m["title"].lower()
        or keyword.lower() in m["genre"].lower()
        or keyword.lower() in m["language"].lower()
    ]

    if not result:
        return {"message": "No results found"}

    return {"results": result, "total_found": len(result)}


# -------------------- Q17 --------------------
@app.get("/movies/sort")
def sort_movies(sort_by: str = "ticket_price", order: str = "asc"):
    if sort_by not in ["ticket_price", "title", "duration_mins"]:
        return {"error": "Invalid sort_by"}

    reverse = order == "desc"
    sorted_list = sorted(movies, key=lambda x: x[sort_by], reverse=reverse)

    return {"sorted": sorted_list}


# -------------------- Q18 --------------------
@app.get("/movies/page")
def paginate(page: int = 1, limit: int = 3):
    start = (page - 1) * limit
    total = len(movies)

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": math.ceil(total / limit),
        "data": movies[start:start + limit]
    }


# -------------------- Q19 --------------------
@app.get("/bookings/search")
def search_booking(name: str):
    return [b for b in bookings if name.lower() in b["customer_name"].lower()]


@app.get("/bookings/sort")
def sort_booking(order: str = "asc"):
    return sorted(bookings, key=lambda x: x["total_cost"], reverse=(order == "desc"))


# -------------------- Q20 --------------------
@app.get("/movies/browse")
def browse(
    keyword: Optional[str] = None,
    sort_by: str = "ticket_price",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):
    result = movies

    if keyword:
        result = [m for m in result if keyword.lower() in m["title"].lower()]

    reverse = order == "desc"
    result = sorted(result, key=lambda x: x[sort_by], reverse=reverse)

    start = (page - 1) * limit

    return {
        "total": len(result),
        "page": page,
        "total_pages": math.ceil(len(result)/limit),
        "data": result[start:start+limit]
    }
    