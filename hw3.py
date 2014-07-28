import sys, gzip, collections, math, itertools

#Creates a counts class to keep track of all count and alignment parameters
class Counts:
    def __init__(self):
        #Stores c(e) values
        self.word = collections.defaultdict(int)
        #Stores c(e,f) values
        self.words = collections.defaultdict(int)
        #Stores c(i,l,m) values
        self.alignment = collections.defaultdict(int)
        #Stores c(j,i,l,m) values
        self.alignments = collections.defaultdict(int)

#Creates a model class to store parameters for a given model
class Model:
    #Sets new parameters
    def recalculate(self, counts):
        self.counts = counts
        self.initialize_step = False
        self.initialize_step_2 = False
    #Probability of an alignment -- different for IBM 1 and 2, so won't specify here
    def p(self, e, f, j, i, l, m):
        pass
    #Calculates t parameter
    def t(self, f, e):
        #If it is our first time running IBM 1, set t values to 1/n(e)
        if self.initialize_step:
            return 1.0 / self.counts.word[e]
        #Otherwise, calculate t normally
        else:
            if self.counts.word[e] > 0:
                return self.counts.words[(e, f)] / self.counts.word[e]
            else:return 0
    #Given an English sentence and a German sentence, produces a list containing alignment values
    def align(self, esent, fsent):
        l = len(esent)
        m = len(fsent)
        alignment = []
        #For each word in the German sentence, find the alignment with the highest probability
        for i, f_i in enumerate(fsent):
            j, p = argmax([(j, self.p(e_j, f_i, j, i, l, m)) for j, e_j in enumerate(esent)])
            alignment.append(j)
        return alignment

#Creates a special class for IBM Model 1
class IBM1(Model):
    def __init__(self, counts):
        #Tells Model class to calculate t parameters as 1/n(e) for this iteration
        self.initialize_step = True
        self.initialize_step_2 = False
        self.counts = counts
    #In IBM Model 1, p only depends on t parameters
    def p(self, e, f, j, i, l, m):
        return self.t(f, e)

#Creates a special class for IBM Model 2
class IBM2(Model):
    #Initiates using IBM Model 1
    def __init__(self, model1):
        self.initialize_step = False
        #Indicates that this is our first time running IBM Model 2, important for setting q parameters
        self.initialize_step_2 = True
        self.counts = model1.counts
    #Sets q parameters
    def q(self, j, i, l, m):
        if self.initialize_step_2:
            return 1.0 / (l + 1.0)
        else:
            if self.counts.alignment[(i,l,m)] > 0.0:
                return self.counts.alignments[(j, i, l, m)] / self.counts.alignment[(i, l, m)]
            else:
                return 0.0
    #Defines p parameters for model 2, where p depends on t and q parameters
    def p(self, e, f, j, i, l, m):
        return self.t(f,e) * self.q(j, i, l, m)

#Creates a counter class to calculate initial counts from the corpus and update them using the EM algorithm
class Counter:
    def __init__(self, english_corpus, german_corpus):
        #Matches each sentence in the English corpus with the corresponding sentence in the German corpus
        self.both = zip(english_corpus, german_corpus)
    #Runs through the corpus and populates the Counts class dictionaries 
    def initialize_counts(self):
        #Creates new instance of Counts class
        self.initial_counts = Counts()
        #For each pair of sentences in the corpus
        for e, f in self.both:
            #For each English word in the sentence
            for e_j in e:
                #For each German word in the sentence
                for f_i in f:
                    key = (e_j, f_i)
                    #Checks if word pair is in words dictionary; if not, adds it
                    if key not in self.initial_counts.words:
                        self.initial_counts.words[key] = 1.0
                        #Checks if English word is in word dictionary; if not, adds it
                        if e_j not in self.initial_counts.word:
                            self.initial_counts.word[e_j] = 1.0
                        #If so, increments it
                        else:
                            self.initial_counts.word[e_j] += 1.0
                    #If so, increments it
                    else:
                        self.initial_counts.words[key] += 1.0
        print "Done initializing..."
        return self.initial_counts
    #Updates parameters according to the IBM Model 1
    def estimate_counts(self, model):
        #Creates new instance of Counts class
        counts = Counts()
        #For each pair of sentences
        for k, (e, f) in enumerate(self.both):
            #Sets l and m length variables
            l = len(e)
            m = len(f)
            #For each word in the German sentence
            for i, f_i in enumerate(f):
                #Calculates denominator of delta value
                denominator = sum((model.p(e_j, f_i, j, i, l, m) for (j, e_j) in enumerate(e)))
                #For each word in the English sentence, increment each count by delta
                for j, e_j in enumerate(e):
                    if denominator > 0.0:
                        delta = model.p(e_j, f_i, j, i, l, m) / denominator
                    else:
                        delta = 0
                    counts.words[(e_j, f_i)] += delta
                    counts.word[e_j] += delta
                    counts.alignments[(j, i, l, m)] += delta
                    counts.alignment[(i, l, m)] += delta
        return counts

#Takes two files, opens them, and splits each line into lists
def split_corpus(english_corpus, german_corpus):
    en = gzip.open(english_corpus, 'rb')
    de = gzip.open(german_corpus, 'rb')
    english = [esentence.split() + ['NULL'] for esentence in en]
    german = [gsentence.split() for gsentence in de]
    return english, german

#Helper argmax function
def argmax(l):
    if not l:
        return None, 0
    else:
        return max(l, key = lambda x: x[1])

#Main code for EM algorithm
def EM(counter, model, iterations):
    for i in range(iterations):
        print "Iteration " + str(i + 1) + "..."
        #Calls the Counter class to re-estimate the parameters for the model
        counts = counter.estimate_counts(model)
        #Updates the model with the new parameters
        model.recalculate(counts)
    print "Done"
    return model

#Main code to generate IBM Model 1
def implement_IBM1(english_corpus, german_corpus):
    english, german = split_corpus(english_corpus, german_corpus)
    #Initializes counter for model
    counter = Counter(english, german)
    #Calculates initial parameters for model
    counts = counter.initialize_counts()
    #Creates model using counts
    model = IBM1(counts)
    #Runs EM algorithm 5 times
    model = EM(counter, model, 5)
    return model

#Takes a file of English words and a model and for each word, returns the top 10 German words and t parameters
def top10(english_file, model):
    f = open(english_file, 'r')
    #Initializes empty list to store English words from file
    english_list = []
    #Reads through the file and appends each word in the file to english_list
    for line in f:
        english_list.append(line.strip())
    #For each word in the list, generate a list of possible German translations and return the highest-scoring ones
    for english_word in english_list:
        possible_german = []
        #For word pairs in our counts dictionary, finds the pairs with english_word and adds the German word in the pair to our list
        for (e,f) in model.counts.words.keys():
            if e == english_word:
                possible_german.append(f)
        #Prints English word, followed by possible translations
        print "\n" + english_word
        #Returns top 10 candidates from possible_german
        for i in range(10):
            german_word, t = argmax ([(german_word, model.t(german_word, english_word)) for german_word in possible_german])
            print german_word, t
            #Removes chosen candidate from possible_german, increments counter i
            possible_german.remove(german_word)
            i += 1

#Calculates alignments for the first k sentences of english_corpus and german_corpus in a given model
def align_sentences(model, k, english_corpus, german_corpus):
    english, german = split_corpus(english_corpus, german_corpus)
    #For each pair of sentences, find the alignment using the model
    for i in range(k):
        alignment = model.align(english[i], german[i])
        #Print the English sentence, German sentence, and the alignment
        print " ".join(english[i]) + "\n" + " ".join(german[i]) + "\n" + str(alignment) + "\n"

#Main code to generate IBM Model 2
def implement_IBM2(model1, english_corpus, german_corpus):
    english, german = split_corpus(english_corpus, german_corpus)
    counter = Counter(english, german)
    #Initializes model using IBM Model 1
    model = IBM2(model1)
    #Removes model1 from memory
    del model1
    #Runs EM algorithm 5 times
    model = EM(counter, model, 5)
    return model

def unscramble(model, german_text, english_text):
    original = open(german_text, 'r')
    scrambled = open(english_text, 'r')
    output = open('unscrambled.en', 'w')
    german = [g.split() for g in original]
    english = [e.split() for e in scrambled]
    P = {}
    for i, f in enumerate(german):
        for j, e in enumerate(english):
            l = len(e)
            m = len(f)
            a = model.align(e, f)
            inner_product = {}
            for i in range(m):
                inner_product[i] = model.p(e[a[i]], f[i], j, i, l, m)
                if inner_product[i] <= 0:
                    inner_product[i] = 1.0 / 100000000000000.0
            P[j] = sum(math.log(inner_product[i], 2) for i in range(m))
        english_sentence, P_value = argmax([(e, P[j]) for j, e in enumerate(english)])
        output.write(str(" ".join(english_sentence)) + "\n")
    output.close()
            #possible_alignments = itertools.combinations_with_replacement(range(l), m)
            #for a in possible_alignments:
                #inner_product = {}
                #if model.p(e[a[i]], f[i], j, i, l, m) == 0:
                    #if model.q(a[i], i, l, m)*model.t(f[i], e[a[i]]) == 0:
                    #inner_product[a[i]] = -100000000
                #else:
                    #inner_product[a[i]] = model.p(e[a[i]], f[i], j, i, l, m)
            #P[f,a,e] = sum(math.log(inner_product[a[i]] for a[i] in a), 2)
            #print P[f,a,e]
            #print model.q(a[i], i, l, m), model.t(f[i], e[a[i]])
            #P[f,a,e] = sum(math.log(model.q(a[i], i, l, m) * model.t(f[i], e[a[i]]), 2) for a in possible_alignments)
            #print P[f,a,e]

#for i, f_i in enumerate(fsent):
            #j, p = argmax([(j, self.p(e_j, f_i, j, i, l, m)) for j, e_j in enumerate(esent)])
            #alignment.append(j)
        #return alignment