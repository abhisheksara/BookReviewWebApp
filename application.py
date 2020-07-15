import os
import requests
from flask import Flask, session, redirect, url_for, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def login():
    return render_template("login.html",message="Welcome!")    

@app.route("/create")
def create():
	message = "Select your username and password"
	return render_template("register.html", message=message)

@app.route("/create/register", methods=["POST"])
def register():
	username=request.form.get("username")
	password=request.form.get("password")

	if username=="" or password=="":
		message="All fields are mandatory"
		return render_template("register.html",message=message)

	elif db.execute("SELECT * FROM users WHERE (username=:username)",{"username":username}).rowcount!=0:
		return render_template("register.html", message="Username already exists \n Try again")	
	else:
		db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",{"username":username,"password":password})
		db.commit()
		return render_template("login.html", message="You have registered successfully \nSign in with your username and password")
		
@app.route("/login", methods=["GET","POST"])
def user():
	if request.method=='GET':
		return render_template("login.html",message="Login with your username and password")

	#if method is post 
	username=request.form.get("username")
	password=request.form.get("password")

	if username=="" or password=="":
		message="All fields are mandatory"
		return render_template("login.html",message=message)

	elif db.execute("SELECT * FROM users WHERE (username=:username) AND (password=:password)",{"username":username, "password":password}).rowcount==0:
		return render_template("login.html", message="Invalid Credentials! \n Try again")	
	else:
		account=db.execute("SELECT * FROM users WHERE (username=:username) AND (password=:password)",{"username":username, "password":password}).fetchone()
		session['loggedin']=True
		session['id']=account.id
		session['username']=account.username
		return render_template("search.html", message=f"You are logged in as {session['username']} \n Search for a book")


@app.route("/login/logout")
def logout():
	session.pop('loggedin',None)
	session.pop('id',None)
	session.pop('username',None)
	return redirect(url_for('login'))

@app.route("/user/search", methods=["POST"])
def search():
	if 'loggedin' in session:
		query=request.form.get("query")

		if query=="":
			return render_template("search.html", message="Please enter the title of the book, author's name or ISBN number of the book you want to search for")

		elif db.execute("SELECT * FROM books WHERE (isbn LIKE :query) OR (author LIKE :query) OR (author LIKE :querycaps) OR (title LIKE :query) OR (title LIKE :querycaps)",
			{"query":'%'+query+'%',"querycaps":'%'+query.capitalize()+'%'}).rowcount==0:
			return render_template("search.html", message="Sorry! We did not find any matching results")

		else:
			count=db.execute("SELECT * FROM books WHERE (isbn LIKE :query) OR (author LIKE :query) OR (author LIKE :querycaps) OR (title LIKE :query) OR (title LIKE :querycaps)",
			{"query":'%'+query+'%',"querycaps":'%'+query.capitalize()+'%'}).rowcount
			books=db.execute("SELECT * FROM books WHERE (isbn LIKE :query) OR (author LIKE :query) OR (author LIKE :querycaps) OR (title LIKE :query) OR (title LIKE :querycaps)",
			{"query":'%'+query+'%',"querycaps":'%'+query.capitalize()+'%'}).fetchall()
			return render_template("results.html", message=f"We found {count} matching results",books=books)
	else:#user is not logged in
		return redirect(url_for('login'))					

@app.route("/books")
def books():
	if 'loggedin' in session:
		books=db.execute("SELECT * FROM books")
		return render_template("results.html", message="Select your book",books=books)
	else:#user is not logged in
		return redirect(url_for('login'))	

@app.route("/books/<int:book_id>")
def book(book_id):
	if 'loggedin' in session:
		book = db.execute("SELECT * FROM books WHERE id=:id", {"id": book_id}).fetchone()
		if book is None:
			return render_template("error.html", message="Sorry, no such book exists")

		isbn=book.isbn
		res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "r0FmiZ3t7dMvGQRRj0ULYg", "isbns":isbn})
		try:	
			if res.status_code!=200:
				raise Exception("ERROR API REQUEST UNSUCCESSFUL")
		except Exception:
			avg_rating="NA"
			rating_count="NA"
		else:
			data=res.json()	
			avg_rating=data['books'][0]['average_rating']
			rating_count=data['books'][0]['work_ratings_count']

		#Get all reviews with given book id
		reviews = db.execute("SELECT review, rating, book_id, username FROM users JOIN reviews ON reviews.user_id = users.id WHERE book_id=:book_id",{"book_id":book_id}).fetchall()
		#select users who reviewd this book
		return render_template("book.html",book=book,rating=avg_rating,rating_count=rating_count,reviews=reviews,message="")
	else:#user is not logged in
		return redirect(url_for('login'))		

@app.route("/books/<int:book_id>/review", methods=["POST"])
def review(book_id):
	rating=request.form.get("rating")
	review=request.form.get("review")
	if 'loggedin' in session:
		book = db.execute("SELECT * FROM books WHERE id=:id", {"id": book_id}).fetchone()
		reviews = db.execute("SELECT review, rating, book_id, user_id, username FROM users JOIN reviews ON reviews.user_id = users.id WHERE book_id=:book_id",{"book_id":book_id}).fetchall()
		#select users who reviewd this book
		#check if user already gave a review for this book
		#check if current user id exists in database for all the reviews with the book_id for this book
		reviewed_ids=[review.user_id for review in reviews]

		isbn = book.isbn
		res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "r0FmiZ3t7dMvGQRRj0ULYg", "isbns":isbn})
		try:	
			if res.status_code!=200:
				raise Exception("ERROR API REQUEST UNSUCCESSFUL")
		except Exception:
			avg_rating="NA"
			rating_count="NA"
		else:
			data=res.json()	
			avg_rating=data['books'][0]['average_rating']
			rating_count=data['books'][0]['work_ratings_count']

		if session['id'] not in reviewed_ids:
			db.execute("INSERT INTO reviews (book_id, user_id, review, rating) VALUES (:book_id, :user_id, :review, :rating)",{"book_id":book_id,"user_id":session['id'],"review":review,"rating":rating})
			db.commit()
			return render_template("book.html",book=book,reviews=reviews,message=f"You submitted review as {session['username']}")
		else:#user has already submiited a review	
			return render_template("book.html",book=book,rating=avg_rating,rating_count=rating_count,reviews=reviews,message="You have already submitted a review for this book ")
	else:#if user is not logged in and method is post				
		return redirect(url_for('login'))

@app.route("/books/api/<isbn>")
def book_api(isbn):
	book = db.execute("SELECT * FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
	if book is None:
		return jsonify({"error":"ISBN not found in database"}),404

	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "r0FmiZ3t7dMvGQRRj0ULYg", "isbns":isbn})
	try:
		if res.status_code!=200:
			raise Exception("ERROR API REQUEST UNSUCCESSFUL")
	except Exception:
		avg_rating="NA"
		rating_count="NA"
	else:
		data=res.json()	
		avg_rating=data['books'][0]['average_rating']
		rating_count=data['books'][0]['work_ratings_count']

	return jsonify({
		"title": book.title,
		"author": book.author,
		"year": book.year,
		"isbn": book.isbn,
		"review_count": rating_count,
		"average_score": avg_rating
	})	