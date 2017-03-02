#!/usr/bin/env python

# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START imports]
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
# [END imports]

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


class Genre(ndb.Model):
    genre_name = ndb.StringProperty(indexed=True)
    song_list = ndb.StructuredProperty(Song, repeated=True)


# Should contain
#   Links to each genre
#   Link to search page
#   Link to song entry page
class MainPage(webapp2.RequestHandler):

    def get(self):
        library_name = DEFAULT_LIBRARY_NAME
        genre_entity_list = Genre.query(ancestor=get_library_key(
            library_name)).fetch(DEFAULT_SONG_NUMBER)
        genre_list = []
        for genre in genre_entity_list:
            genre_list.append(genre.genre_name.title())

        print(genre_list)

        template = JINJA_ENVIRONMENT.get_template('mainpage.html')
        self.response.write(template.render(genres=genre_list))


# Should contain
#   List of all songs in that Genre
#   return to main page link
class GenrePage(webapp2.RequestHandler):

    def get(self):
        print self.request.get('genre_name', DEFAULT_GENRE_NAME)
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()
        if contains_genre(genre_name):
            print genre_name
            genre_key = get_genre_key(genre_name)
            genre_obj = genre_key.get()
            song_list = genre_obj.song_list
            genre_name = genre_obj.genre_name.title()

            for song in song_list:
                song.artist = song.artist.title()
                song.title = song.title.title()
                song.album = song.album.title()

            template = JINJA_ENVIRONMENT.get_template('genre_display.html')
            self.response.write(template.render(
                genre=genre_name, song_list=song_list))
        else:
            template = JINJA_ENVIRONMENT.get_template('genre_display.html')
            self.response.write(template.render(genre=genre_name, song_list=[]))

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
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()
        template_values = {
            'genre_name': genre_name.title(),
            'message': '',
        }
        template = JINJA_ENVIRONMENT.get_template('create_song.html')
        self.response.write(template.render(template_values))

    def post(self):
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()
        if not contains_genre(genre_name):
            print 'here'
            message = 'Genre has not been created or was misspelled'
        else:
            artist = self.request.get('artist').lower()
            title = self.request.get('title').lower()
            album = self.request.get('album').lower()
            print genre_name + artist + title + album
            if artist == '' or title == '':
                message = 'Title or Artist was left blank'
            else:
                genre_obj = get_genre_key(genre_name).get()
                current_list = genre_obj.song_list
                print 'current_list = '
                print current_list
                new_song = Song(parent=get_genre_key(genre_name),
                                title=title, artist=artist, album=album)
                new_song.put()
                new_list = current_list + [new_song]
                genre_obj.song_list = new_list
                genre_obj.put()
                print genre_obj.song_list
                message = 'Created song in genre ' + genre_name.title() + ': Title: ' + \
                    new_song.title.title() + ', Artist: ' + new_song.artist.title()
                if new_song.album != '':
                    message += ', Album: ' + new_song.album.title()
        template_values = {
            'genre_name': genre_name.title(),
            'message': message,
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
        template = JINJA_ENVIRONMENT.get_template('create_genre.html')
        template_values = {
            'new_genre': '',
            'message': '',
        }
        self.response.write(template.render(template_values))

    def post(self):
        library_name = DEFAULT_LIBRARY_NAME
        new_genre = self.request.get('new_genre').lower()
        if ' ' in new_genre:
            message = "Spaces in message not allowed"
        else:
            print 'New Genre = ' + new_genre
            genre_obj = Genre(parent=get_library_key(
                library_name), genre_name=new_genre)
            genre_obj.put()
            template = JINJA_ENVIRONMENT.get_template('create_genre.html')
            message = "Created genre: " + new_genre.title()
        template_values = {
            'new_genre': new_genre.title(),
            'message': message,
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
        template = JINJA_ENVIRONMENT.get_template('search.html')
        genre_name = self.request.get('genre_name', DEFAULT_GENRE_NAME).lower()
        new_page = 0
        if self.request.get('genre_name').lower() == '':
            new_page = 1
            genre_name = DEFAULT_GENRE_NAME
        artist = self.request.get('artist').lower()
        print genre_name + artist
        if artist != '':
            # genre_key = get_genre_key(genre_name)
            # all_song_list_query = Song.query(ancestor=genre_key)
            # print all_song_list_query.fetch(DEFAULT_SONG_NUMBER)
            # filtered_list_query = all_song_list_query.filter(Song.artist == artist)
            # song_list = filtered_list_query.fetch(DEFAULT_SONG_NUMBER)
            # print 'genre_current_list = '
            # print  song_list

            genre_key = get_genre_key(genre_name)
            genre_obj = genre_key.get()
            song_list = genre_obj.song_list
            filtered_list = []
            for song in song_list:
                if artist.lower() in song.artist.lower():
                    song.artist = song.artist.title()
                    song.title = song.title.title()
                    song.album = song.album.title()
                    filtered_list.append(song)
            if filtered_list == []:
                message = 'No songs found'
            else:
                message = 'Found songs in ' + genre_name

            template_values = {
                'genre_name': genre_name.title(),
                'song_list': filtered_list,
                'message': message,
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
            }
            self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/display/*', GenrePage),
    ('/search/*', SearchPage),
    ('/search', SearchPage),
    ('/create_song', CreateSongPage),
    ('/create_genre', CreateGenrePage),
], debug=True)
# [END app]
