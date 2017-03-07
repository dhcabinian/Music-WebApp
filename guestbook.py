#!/usr/bin/env python

import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

DEFAULT_GENRE_NAME = 'Trap'
DEFAULT_LIBRARY_NAME = 'David\'s Library'
DEFAULT_SONG_NUMBER = 50


def get_library_key(library_name=DEFAULT_LIBRARY_NAME):
    return ndb.Key('Library', library_name)


def get_genre_key(genre_name=DEFAULT_GENRE_NAME):
    library_name = DEFAULT_LIBRARY_NAME
    genre_entity_list = Genre.query(ancestor=get_library_key(
        library_name)).fetch(DEFAULT_SONG_NUMBER)
    for genre in genre_entity_list:
        if genre.genre_name == genre_name:
            return genre.key
    return None


class Song(ndb.Model):
    title = ndb.StringProperty(indexed=True)
    artist = ndb.StringProperty(indexed=True)
    album = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    price = ndb.FloatProperty(indexed=False)
    price_format = ndb.StringProperty(indexed=False)
    url_string = ndb.StringProperty(indexed=False)


class Genre(ndb.Model):
    genre_name = ndb.StringProperty(indexed=True)
    song_list = ndb.StructuredProperty(Song, repeated=True)


class Cart(ndb.Model):
    song_list = ndb.StructuredProperty(Song, repeated=True)
    subtotal = ndb.FloatProperty(indexed=False)
    subtotal_format = ndb.StringProperty(indexed=False)


class Purchase(ndb.Model):
    song_list = ndb.StructuredProperty(Song, repeated=True)
    subtotal = ndb.FloatProperty(indexed=False)
    subtotal_format = ndb.StringProperty(indexed=False)
    dateTime = ndb.DateTimeProperty(auto_now_add=True)
    user = ndb.UserProperty()
    user_id = ndb.StringProperty(indexed=False)


class User(ndb.Model):
    cart = ndb.StructuredProperty(Cart)
    user = ndb.UserProperty()
    user_id = ndb.StringProperty()



def checkUser(user):
    user_key = ndb.Key(User, user.user_id())
    if user_key.get() is not None:
        user_obj = user_key.get()
        cart_obj = user_obj.cart
        return user_obj, cart_obj
    else:
        new_user_key = ndb.Key(User, user.user_id())
        new_user = User(key=new_user_key)
        new_user.user=user
        new_user_key = new_user.put()
        new_cart = Cart()
        new_cart.parent=new_user.key
        new_cart.subtotal=0
        new_cart.subtotal_format='${:,.2f}'.format(0)
        new_cart.song_list = []
        new_cart_key = new_cart.put()
        new_user.cart = new_cart
        new_user.put()
        return new_user, new_cart

#Returns things in tne following
# [foundUser, url, url_linktext, user_obj, cart_obj]
def performUserFunctions(handler):
    user = users.get_current_user()
    foundUser = False
    if user:
        url = users.create_logout_url(handler.request.uri)
        nickname = user.nickname()
        url_linktext = 'Logout from ' + nickname
        user_obj, cart_obj = checkUser(user)
        foundUser = True
        return foundUser, url, url_linktext, user_obj, cart_obj
    else:
        url = users.create_login_url(handler.request.uri)
        url_linktext = 'Login'
        return [foundUser, url, url_linktext, None, None]

#Titilizes song List

def titilizeSongList(song_list):
    for song in song_list:
        song.artist = song.artist.title()
        song.title = song.title.title()
        song.album = song.album.title()


# Should contain
#   Links to each genre
#   Link to search page
#   Link to song entry page
class MainPage(webapp2.RequestHandler):
    def get(self):
        # Genre List Generation
        library_name = DEFAULT_LIBRARY_NAME
        genre_entity_list = Genre.query(ancestor=get_library_key(
            library_name)).fetch(DEFAULT_SONG_NUMBER)
        genre_list = []
        for genre in genre_entity_list:
            genre_list.append(genre.genre_name.title())

        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        # Rendering
        template_values = {
            'genres': genre_list,
            'url': url,
            'url_linktext': url_linktext,
        }
        template = JINJA_ENVIRONMENT.get_template('mainpage.html')
        self.response.write(template.render(template_values))


# Should contain
#   List of all songs in that Genre
#   return to main page link
class GenrePage(webapp2.RequestHandler):
    def get(self):
        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        # Genre List Generation
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()
        if contains_genre(genre_name):
            genre_key = get_genre_key(genre_name)
            genre_obj = genre_key.get()
            song_list = genre_obj.song_list
            # Converting back to uppercase
            genre_name = genre_obj.genre_name.title()
            titilizeSongList(song_list)

            # Rednering
            template_values = {
                'genre': genre_name,
                'song_list': song_list,
                'url': url,
                'url_linktext': url_linktext,
                'message': '',
            }
            template = JINJA_ENVIRONMENT.get_template('genre_display.html')
            self.response.write(template.render(template_values))
        else:
            # Rendering
            template_values = {
                'genre': genre_name,
                'song_list': [],
                'url': url,
                'url_linktext': url_linktext,
                'message': '',
            }
            template = JINJA_ENVIRONMENT.get_template('genre_display.html')
            self.response.write(template.render(template_values))

    def post(self):
        # User Login
        message = ''
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)
        if not foundUser:
            message = 'Please login in order to add things to cart.'

        # Genre List Generation
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()
        if contains_genre(genre_name):
            genre_key = get_genre_key(genre_name)
            genre_obj = genre_key.get()
            song_list = genre_obj.song_list
            # Converting back to uppercase
            genre_name = genre_obj.genre_name.title()
            titilizeSongList(song_list)


            if foundUser:
                numOfSongs = int(self.request.get('numOfSongs', 0))
                added_songs = []
                for index in range(0, numOfSongs):
                    htmlName = 'Song' + str(index)
                    song_url_string = self.request.get(htmlName, '')
                    if song_url_string is not '':
                        added_songs.append(song_url_string)
                new_cart_song_list = cart_obj.song_list
                for song_url_string in added_songs:
                    song_key = ndb.Key(urlsafe=song_url_string)
                    song_obj = song_key.get()
                    new_cart_song_list = new_cart_song_list + [song_obj]
                cart_obj.song_list = new_cart_song_list
                cart_obj.put()
                user_obj.cart = cart_obj
                user_obj.put()
                message = 'Added new songs to cart.'

            # Rednering
            template_values = {
                'genre': genre_name,
                'song_list': song_list,
                'url': url,
                'url_linktext': url_linktext,
                'message': message,
            }
            template = JINJA_ENVIRONMENT.get_template('genre_display.html')
            self.response.write(template.render(template_values))
        else:
            # Rendering
            template_values = {
                'genre': genre_name,
                'song_list': [],
                'url': url,
                'url_linktext': url_linktext,
                'message': message,
            }
            template = JINJA_ENVIRONMENT.get_template('genre_display.html')
            self.response.write(template.render(template_values))

def price_checker(unchecked_price):
    if 0 < unchecked_price <= 100:
        return True
    else:
        return False


# Should contain
#   Artist name box
#   Title box
#   Album box
#   Song enter button
#   Genre select box
#   Genre switch button
#   Return to main page link
class CreateSongPage(webapp2.RequestHandler):
    def get(self):
        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        # Obtaining Genre to add to
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()

        template_values = {
            'genre_name': genre_name.title(),
            'message': '',
            'url': url,
            'url_linktext': url_linktext,
        }
        template = JINJA_ENVIRONMENT.get_template('create_song.html')
        self.response.write(template.render(template_values))

    def post(self):
        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        # Obtaining Genre to add to
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()
        if not contains_genre(genre_name):
            message = 'Genre has not been created or was misspelled'
        else:
            # Convert to lowercase for stoarge and easy matching
            artist = self.request.get('artist').lower()
            title = self.request.get('title').lower()
            album = self.request.get('album').lower()
            # Valid Price Checking
            if self.request.get('price') != '':
                if price_checker(float(self.request.get('price'))):
                    price = float(self.request.get('price'))
                else:
                    price = ''
            else:
                price = ''
            if artist == '' or title == '' or price == '':
                message = 'Title or Artist or Price was left blank or entered incorectly'
            else:
                # Add objects
                genre_obj = get_genre_key(genre_name).get()
                current_list = genre_obj.song_list
                price_format = '${:,.2f}'.format(price)
                new_song = Song(parent=get_genre_key(genre_name),
                                title=title, artist=artist, album=album, price=price, price_format=price_format)
                new_song_key = new_song.put()
                new_song.url_string = new_song_key.urlsafe()
                new_song_key = new_song.put()
                new_list = current_list + [new_song]
                genre_obj.song_list = new_list
                genre_obj.put()
                # Generate messages
                message = 'Created song in genre ' + genre_name.title() + \
                          ': Price: ' + new_song.price_format + ', Title: ' + \
                          new_song.title.title() + ', Artist: ' + new_song.artist.title()
                if new_song.album != '':
                    message += ', Album: ' + new_song.album.title()
        # Rendering
        template_values = {
            'genre_name': genre_name.title(),
            'message': message,
            'url': url,
            'url_linktext': url_linktext,
        }
        template = JINJA_ENVIRONMENT.get_template('create_song.html')
        self.response.write(template.render(template_values))


def contains_genre(genre_name):
    library_name = DEFAULT_LIBRARY_NAME
    genre_entity_list = Genre.query(ancestor=get_library_key(
        library_name)).fetch(DEFAULT_SONG_NUMBER)
    contains = False
    for genre in genre_entity_list:
        if genre.genre_name == genre_name:
            contains = True
    return contains


class CreateGenrePage(webapp2.RequestHandler):
    def get(self):
        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        template = JINJA_ENVIRONMENT.get_template('create_genre.html')
        template_values = {
            'new_genre': '',
            'message': '',
            'url': url,
            'url_linktext': url_linktext,
        }
        self.response.write(template.render(template_values))

    def post(self):
        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        library_name = DEFAULT_LIBRARY_NAME
        new_genre = self.request.get('new_genre').lower()
        if ' ' in new_genre:
            message = "Spaces in message not allowed"
        else:
            genre_obj = Genre(parent=get_library_key(
                library_name), genre_name=new_genre)
            genre_obj.put()
            template = JINJA_ENVIRONMENT.get_template('create_genre.html')
            message = "Created genre: " + new_genre.title()
        template_values = {
            'new_genre': new_genre.title(),
            'message': message,
            'url': url,
            'url_linktext': url_linktext,
        }
        self.response.write(template.render(template_values))


# Should contain
#   artist search box
#   Search button
#   genre box
#   Switch button
#   Return to home link
class SearchPage(webapp2.RequestHandler):
    def get(self):
        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        template = JINJA_ENVIRONMENT.get_template('search.html')
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()
        new_page = 0
        if self.request.get('genre_name').lower() == '':
            new_page = 1
            genre_name = DEFAULT_GENRE_NAME
        artist = self.request.get('artist').lower()
        if artist != '':
            genre_key = get_genre_key(genre_name)
            genre_obj = genre_key.get()
            song_list = genre_obj.song_list
            filtered_list = []
            for song in song_list:
                if artist.lower() in song.artist.lower():
                    filtered_list.append(song)
            titilizeSongList(filtered_list)
            if not filtered_list:
                message = 'No songs found'
            else:
                message = 'Found songs in ' + genre_name.title()

            template_values = {
                'genre_name': genre_name.title(),
                'song_list': filtered_list,
                'message': message,
                'url': url,
                'url_linktext': url_linktext,
            }
            self.response.write(template.render(template_values))
        else:
            if new_page == 1:
                message = ''
            else:
                message = 'No artist entered'
            template_values = {
                'genre_name': genre_name.title(),
                'song_list': [],
                'message': message,
                'url': url,
                'url_linktext': url_linktext,
            }
            self.response.write(template.render(template_values))

class CartPage(webapp2.RequestHandler):
    def get(self):
        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        if foundUser:
            message = 'Your cart:'
            song_list = cart_obj.song_list
            #print 'Cart Page cart obj'

            titilizeSongList(song_list)
            template_values = {
                'song_list': song_list,
                'message': message,
                'url': url,
                'url_linktext': url_linktext,
            }
            template = JINJA_ENVIRONMENT.get_template('cart.html')
            self.response.write(template.render(template_values))
        else:
            message = 'Please log in in order to see your cart.'
            template_values = {
                'song_list': [],
                'message': message,
                'url': url,
                'url_linktext': url_linktext,
            }
            template = JINJA_ENVIRONMENT.get_template('cart.html')
            self.response.write(template.render(template_values))

    def post(self):
        # User Login
        foundUser, url, url_linktext, user_obj, cart_obj = performUserFunctions(self)

        if foundUser:
            message = 'Your cart:'
            song_list = cart_obj.song_list
            titilizeSongList(song_list)
            template_values = {
                'song_list': song_list,
                'message': message,
                'url': url,
                'url_linktext': url_linktext,
            }
            template = JINJA_ENVIRONMENT.get_template('cart.html')
            self.response.write(template.render(template_values))
        else:
            message = 'Please log in in order to see and make changes to your cart.'
            template_values = {
                'song_list': [],
                'message': message,
                'url': url,
                'url_linktext': url_linktext,
            }
            template = JINJA_ENVIRONMENT.get_template('cart.html')
            self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/display/*', GenrePage),
    ('/search/*', SearchPage),
    ('/search', SearchPage),
    ('/create_song', CreateSongPage),
    ('/create_genre', CreateGenrePage),
    ('/cart', CartPage),
], debug=True)
