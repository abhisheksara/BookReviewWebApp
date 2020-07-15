# abhisheksara

Hello!

This project is a web application for book reviews where users can register, login, search for a book, see the rating and reviews given by other users, and submit their review for the book.

'import.py' is the python file I used to import data from a csv file into the database on heroku.

The database is hosted on Heroku. I have used three tables to keep a track of user accounts, books and reviews. I linked the reviews with foregin keys referring to the userid and bookid in the users and books table to kep a track of the user who has submitted a review and the book for which it has been submitted.

I used flask to build the application in the file 'application.py' and used SQLAlchemy to establish interaction between the application and the database.

I used session to keep track of logins and logouts by adding and popping variables appropriately.

After creating an account and loggin in, you can search for a book by its title, isbn number, author name or year by typing even a part of the title, number or name. The app then shows the results matching your query. 

Users can submit ONE review for each book consisting of a rating on a scale of 1 to 5 and a text content. 

On the book page, average rating and number of ratings received on goodreads are shown if available using the goodreads API.

Users can make a get request to "/books/api/<isbn>" and get a JSON respone of the title, author, publication date, ISBN number, review count and average score
