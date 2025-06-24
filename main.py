from datetime import date
from typing import List
import flask
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Importing forms from the forms.py
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
import smtplib

my_email="mondalrehan215@gmail.com"
email_password="urxmpxzfybhxqeuj"


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

#-------------------------------------------------------------------------CONFIGURING FLASK LOGIN-------------------------------------------------------------#
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# -------------------------------------------------------------------------------CREATED DATABASE--------------------------------------------------------------#
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


#------------------------------------------------------------------------------- CONFIGURING TABLES------------------------------------------------------------#
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Creating Foreign Key, "users.id" the users refers to the tablename of User.
    author_id: Mapped[int] = mapped_column(ForeignKey("user_table.id"))
    # Create reference to the User object. The "posts" refers to the posts property in the User class.
    author: Mapped["User"] = relationship(back_populates="posts")
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    # Parent relationship to the comments
    comments: Mapped[List["Comment"]] = relationship(back_populates="parent_post",cascade="all, delete-orphan")

#--------------------------------------------------------------------------------USER TABLE---------------------------------------------------------------------#
class User(UserMixin,db.Model):
    __tablename__ = "user_table"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))

    # This will act like a list of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts: Mapped["BlogPost"] = relationship(back_populates="author")
    # Parent relationship: "author" refers to the author property in the Comment class.
    comments: Mapped["Comment"] = relationship(back_populates="author")
    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password
#-----------------------------------------------------------------------------CREATING DATABASE FOR COMMENTATORS-------------------------------------------------#
class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    # Child relationship:"users.id" The users refers to the tablename of the User class.
    # "comments" refers to the comments property in the User class.
    author_id: Mapped[int] = mapped_column(ForeignKey("user_table.id"))
    author: Mapped["User"] = relationship(back_populates="comments")

    # Child Relationship to the BlogPosts
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()

#-----------------------------------------------------------CREATING ADMIN ONLY DECORATOR SO ONLY ADMIN CAN ACCESS CERTAIN ROUTES---------------------------------------------#
def admin_only(function):
    @wraps(function)
    def decorator_function(*args,**kwargs):
        if current_user.id==1:
            return function(*args,**kwargs)
        else:
            flask.abort(403)
    return decorator_function
#----------------------------------------------------------USING GRAVATAR TO CREATE AVATAR FOR COMMENTATORS------------------------------------------------------------------#
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)
#-------------------------------------------------------------------USING WERKZEUG TO HASH THE USER'S PASSWORD----------------------------------------------------------------#
#-------------------------------------------------------------------REGISTERING NEW USER IN BLOG -----------------------------------------------------------------------------#
@app.route('/register',methods=["POST","GET"])
def register():
    form=RegisterForm()
    if form.validate_on_submit():
        name=form.name.data
        email=form.email.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        password=form.password.data
        hashed_password=generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user=User(email=email,password=hashed_password,name=name)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html",form=form,logged_in=current_user.is_authenticated)


#-----------------------------------------------------------RETRIEVING A USER BASED ON THEIR EMAIL----------------------------------------------------------------------#
#-----------------------------------------------------------LOGGING IN EXISTING USER IN DATABASE IN BLOG----------------------------------------------------------------#
@app.route('/login',methods=["POST","GET"])
def login():
    form=LoginForm()
    if request.method=='POST':
        email=form.email.data
        user=db.session.execute(db.select(User).where(User.email==email)).scalar()
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, form.password.data):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html",form=form,logged_in=current_user.is_authenticated)

#----------------------------------------------------------------------------LOG OUT ROUTE----------------------------------------------------------------#
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

#----------------------------------------------------------------------------HOME ROUTE ----------------------------------------------------------------#
@app.route('/', methods=["GET","POST"])
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts,logged_in=current_user.is_authenticated,user=current_user)


#---------------------------------------------------------------LOGGED IN USERS ACCESSING COMMENTS------------------------------------------------------------#
@app.route("/post/<int:post_id>",methods=["GET","POST"])
@login_required
def show_post(post_id):
    form=CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        new_comment = Comment(
            text=form.comment.data,
            author_id=current_user.id,
            post_id=requested_post.id
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post,user=current_user,logged_in=current_user.is_authenticated,form=form)


#----------------------------------------------------------- ONLY ALLOWING ADMIN TO CREATE POST-------------------------------------------------------------#
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


#-----------------------------------------------------------ONLY ALLOWING ADMIN TO EDIT POST------------------------------------------------------------------#
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


#-------------------------------------------------------------------------ONLY ALLOWING ADMIN TO DELETE POST---------------------------------------------------#
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact",methods=["GET","POST"])
def contact():
    if request.method == "POST":
        data=request.form
        name=data["name"]
        phone=data["phone"]
        email=data["email"]
        message=data["message"]
        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(my_email, email_password)
            connection.sendmail(from_addr=my_email, to_addrs=my_email, msg=f"Subject: Contact ME Form\n\n"
                                                                           f"Name : {name}\n"
                                                                           f"Phone : {phone}\n"
                                                                           f"Email : {email}\n"
                                                                           f"Message : {message}\n")
        message_sent=True
        return render_template("contact.html",msg_sent=message_sent)
    elif request.method == "GET":
        head_get="Contact Me"
        return render_template("contact.html")
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=5002)
