import requests
import math
from html.parser import HTMLParser


class MyHTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        self.title_wrapper_position = -1
        self.title = ""
        self.story = ""
        self.storyline = False
        self.get_story = False
        self.recommended = []
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):
        if tag == 'div' and len(attrs) > 0 and attrs[0][0] == 'class' and attrs[0][1] == 'title_wrapper':
            self.title_wrapper_position = self.getpos()[0]
        if tag == 'span' and len(attrs) == 0 and self.storyline:
            self.get_story = True
        if tag == 'div' and len(attrs) == 4 and attrs[0][0] == 'class' and attrs[0][1] == 'rec_item':
            self.recommended.append(attrs[3][1])

    def handle_endtag(self, tag):
        if tag == 'span' and self.storyline:
            self.storyline = False
            self.get_story = False

    def handle_data(self, data):
        if self.title_wrapper_position != -1 and self.getpos()[0] >= self.title_wrapper_position:
            if data.strip() == "":
                return
            self.title = data.strip()
            self.title_wrapper_position = -1
        if data.strip() == 'Storyline':
            self.storyline = True
        if self.get_story:
            if data.strip() == "":
                return
            self.story = self.story + " " + data.strip()

punctuations = {'#', '[', '~', '-', ']', '.', '@', '/', "'", '{', '|', ')',
                '(', '*', ',', '`', ';', '$', '%', '\\', '^', '_', '!', '<', ':', '&', '>', '"', '}', '=', '?', '+'}
stopwords = {'us', 'for', 'this', 'by', 'few', 'which', 'of', 'why', 'you', 'there', 'them', 'some', 'your', 'her', 'many', 'it', 'will', 'the', 'are', 'all', 'who', 'none', 'they', 'a', 'him', 'an',
             'i', 'where', 'its', 'what', 'as', 'have', 'in', 'his', 'she', 'my', 'be', 'any', 'been', 'how', 'or', 'and', 'me', 'their', 'but', 'on', 'is', 'here', 'our', 'with', 'when', 'that', 'was', 'he'}

def get_movie_contents(imdb_id):
    r = requests.get("https://www.imdb.com/title/"+imdb_id)
    parser = MyHTMLParser()
    parser.feed(r.text)
    ret = [imdb_id, parser.title, parser.story, parser.recommended]
    parser.close()
    return ret

def IMDB_scrap():
    count = 0
    w_file = open("movie_info.txt", "w")
    for line in open("movie_ids.csv"):
        count += 1
        print( count )
        contents = get_movie_contents(line.strip())
        w_file.write(contents[0]+"\n")
        w_file.write(contents[1]+"\n")
        w_file.write(contents[2]+"\n")
        for rec in contents[3]:
            w_file.write(rec + " ")
        w_file.write("\n")

vocabulary = {}
token_to_tokenId = {}
token_counter = 0
movies = []

def tokenize(input):
    input = input.strip()
    without_punc = ""
    for char in input:
        if char in punctuations:
            without_punc += ' '
        else:
            without_punc += char
    tokens = list(map(lambda x: x.lower(), without_punc.split()))
    tokens = list(filter(lambda x: x not in stopwords, tokens))
    return tokens

statistic = []

class Movie():
    def __init__(self, id):
        self.id = id;
        self.vector = []
        self.recommended = []

    def insert_element(self, word, freq):
        self.vector.append((word, freq))

    def insert_rec(self, id):
        self.recommended.append(id)

    def tf_idf(self, N):
        total_sum = 0.0
        for i in range(len(self.vector)):
            word = int(self.vector[i][0])
            freq = int(self.vector[i][1])
            self.vector[i] = (word, (1+math.log10(freq))*math.log10(N/vocabulary[word]) )
            total_sum += self.vector[i][1]
        self.vector.sort(key = lambda tup: tup[1])
        self.vector.reverse()
        sum = 0.0
        for i in range(len(self.vector)):
            sum += self.vector[i][1]
            if sum >= 0.95*total_sum:
                statistic.append(i)
                break

    def take_top_N(self, N):
        self.vector = self.vector[:min(N,len(self.vector))]
        self.vector.sort(key = lambda tup: tup[0])

    def normalize(self):
        length = 0.0
        for elem in self.vector:
            length += elem[1]*elem[1]
        length = math.sqrt(length)
        for i in range(len(self.vector)):
            self.vector[i] = ( self.vector[i][0] , self.vector[i][1]/length)


def read_data_from_file():
    global token_counter
    count = 0
    for line in open("movie_info.txt", "r"):
        line = line.strip()
        if count == 0:
            movie = Movie(line)
            tf = {}
        if count == 1 or count == 2:
            for token in tokenize(line):
                if token not in token_to_tokenId:
                    token_counter += 1
                    token_to_tokenId[token] = token_counter
                if token_to_tokenId[token] not in tf:
                    tf[token_to_tokenId[token]] = 0    
                tf[token_to_tokenId[token]] += 1
        if count == 3:
            for rec in line.split(" "):
                movie.insert_rec(rec)
            for term in tf:
                movie.insert_element(int(term), int(tf[term]))
                if term not in vocabulary:
                    vocabulary[term] = 0
                vocabulary[term] += 1
            movies.append(movie)
        count = (count+1)%4

# IMDB_scrap()
read_data_from_file()

for movie in movies:
    movie.tf_idf(len(movies))

average = 0
for st in statistic:
    average += st/len(statistic)
for movie in movies:
    movie.take_top_N(int(average))
    movie.normalize()


def calc_similarity( movie1, movie2 ):
    i = 0
    j = 0
    similarity = 0.0
    while i < len(movie1.vector) and j < len(movie2.vector):
        if movie1.vector[i][0] == movie2.vector[j][0]:
            similarity += movie1.vector[i][1]*movie2.vector[j][1]
            i += 1
            j += 1
        elif movie1.vector[i][0] < movie2.vector[j][0]:
            i += 1
        else:
            j += 1
    return similarity
        

def recommend(imdb_id):
    for movie in movies:
        if movie.id == imdb_id:
            current_movie = movie
    recommendations = []
    for movie in movies:
        if movie.id == current_movie.id:
            continue
        similarity = calc_similarity(movie , current_movie )
        recommendations.append((movie.id,similarity))
    recommendations.sort(key = lambda tup: tup[1])
    recommendations.reverse()
    recommendations = recommendations[:11]
    return [x for (x,y) in recommendations]

def evaluate_recommendations(rec_movie_ids, relevant_movie_ids, K):
    rec_movie_ids=rec_movie_ids[:K]
    presicion = len(list(filter( lambda x: x in relevant_movie_ids , rec_movie_ids )))/len(rec_movie_ids)
    recall = len(list(filter( lambda x: x in rec_movie_ids , relevant_movie_ids )))/len(relevant_movie_ids)
    try:
        f1_score = 2*presicion*recall/(presicion+recall)
    except Exception as e:
        f1_score = math.nan
    return (presicion,recall,f1_score)


def get_relevant_movie_ids(imdb_id):
    for movie in movies:
        if movie.id == imdb_id:
            return movie.recommended

def get_metrics(imdb_id):
    for k in [1,2,3,10]:
        metrics = evaluate_recommendations(recommend(imdb_id),get_relevant_movie_ids(imdb_id), k)
        print("K = " + str(k))
        print("Presicion = " + str(metrics[0]))
        print("Recall = " + str(metrics[1]))
        print("F1 score = " + str(metrics[2]))
