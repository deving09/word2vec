from __future__ import division, print_function, unicode_literals

import numpy as np
import os
try:
    from sklearn.externals import joblib
except:
    joblib = None

from word2vec.utils import unitvec


class WordVectors(object):

    def __init__(self, vocab, vectors, clusters=None, train=None):
        """
        Initialize a WordVectors class based on vocabulary and vectors

        This initializer precomputes the vectors of the vectors

        Parameters
        ----------
        vocab : np.array
            1d array with the vocabulary
        vectors : np.array
            2d array with the vectors calculated by word2vec
        clusters : word2vec.WordClusters (optional)
            1d array with the clusters calculated by word2vec
        """
        self.vocab = vocab
        self.vectors = vectors
        self.clusters = clusters
        self._buildIndexMap(vocab)
        self.train = train

    def ix(self, word):
        """
        Returns the index on self.vocab and `self.vectors` for `word`
        """
        if word not in self.index_map:
            raise KeyError('Word not in vocabulary')
        else:
            return self.index_map[word]

    def __getitem__(self, word):
        return self.get_vector(word)

    def __contains__(self, word):
        return word in self.index_map

    def _buildIndexMap(self, vocab):
        self.index_map = {}
        for idx, word in enumerate(vocab):
            self.index_map[word] = idx
    
    def trainSentence(self, sentence, epochs=50, alpha=0.05):
        word_list = sentence.split() #prune for valid words
        layer1_size = self.train['layer1_size']
        window = self.train['window']
        newvec =  np.random.random(layer1_size)
        sentence_position = 0
        sentence_len = len(word_list)
        word = word_list[sentence_position]
        step_size = (alpha - min(0.0001, alpha)) / (sentence_len * epochs)
        for epoch in xrange(epochs):
            sentence_position = 0
            while True:
                word = word_list[sentence_position]
                neu1 = np.zeros(layer1_size)
                neu1e = np.zeros(layer1_size)
                b = np.random.randint(0, window)
                if self.train['cbow']:
                    cw = 0
                    for a in xrange(b, window * 1 + 1 - b):
                        c = sentence_position - window + a
                        if c < 0: continue
                        if c >= sentence_len: continue
                        curr_word = word_list[c]
                        neu1 += self.get_vector(curr_word)
                        cw += 1
                    
                    neu1 += newvec
                    cw += 1
                    if cw:
                        neu1 /= cw
                        if self.train['hs']:
                            for d in xrange(self.train["vocab"][word]["codelen"]):
                                f = 0
                                l2 = self.train["vocab"][word]["point"][d]
                                f = 1. / (1 + exp(np.dot(neu1, self.train['syn1'][l2])))
                                g = (1 - self.train['vocab'][word]['code'][d]) * alpha
                                neu1e += g * self.train['syn1'][l2]
                        else:
                            for d in xrange(max([3, self.train['neg']]) + 1):
                                if d == 0:
                                    target = word
                                    label = 1
                                else:
                                    target = self.vocab[np.random.randint(0, self.train['syn1_size'])]
                                    if target ==  word: continue
                                    label = 0
                                
                                l2 = target #self.ix[target]
                                f = 0
                                f = np.dot(neu1, self.train["syn1"][l2])
                                g = (label - 1. / (1 + np.exp(f))) * alpha
                                neu1e += g * self.train["syn1"][l2]
                        
                        newvec += neu1e
                else: #adjusting the tast word logic of this sequence to only learn the sentence embedding
                    if True:
                    #for a in xrange(b, window * 2 + 2 - b):
                        """c = sentence_position - window + a
                        if (a >= window * 2 + 1 - b): c =0
                        if c < 0: continue
                        if c >= sentence_len: continue
                        last_word =  word_list[c]
                        l1 = last_word 
                        """
                        neu1e = np.zeros(layer1_size)
                        if self.train['hs']:
                            for d in xrange(self.train['vocab'][word]['codelen']):
                                f = 0
                                l2 = self.train['vocab'][word]['point'][d]
                                #f += 1. / (1 - np.exp( np.dot(self.get_vector(last_word), self.train['syn1'][l2])))
                                f += 1. / (1 - np.exp( np.clip(np.dot(newvec, self.train['syn1'][l2]), -3., 3.)))
                                g = (1 - self.train['vocab'][word]['code'][d] - f) * alpha
                                neu1e += g * self.train['syn1'][l2]
                        else:
                            for d in xrange(max([3, self.train['neg']]) + 1):
                                if d == 0:
                                    target = word
                                    label = 1
                                else:
                                    target = self.vocab[np.random.randint(0, self.train['syn1_size'])]
                                    if target ==  word: continue
                                    label = 0
                                
                                l2 = target
                                f = 0
                                #f = 1. /(1. + np.exp(np.dot(self.get_vocab(last_word), self.train['syn1'][l2])))
                                f = 1. /(1. + np.exp(np.dot(newvec, self.train['syn1'][l2])))
                                g = (label - f) * alpha
                                neu1e += g * self.train['syn1'][l2]
                            
                            newvec += neu1e
                            #comment out original logic
                            #model.get_vector(last_word) += neu1e
                
                sentence_position += 1
                alpha -= step_size
                if sentence_position >= sentence_len:
                    break
        
        return newvec
        
    def get_vector(self, word):
        """
        Returns the (vectors) vector for `word` in the vocabulary
        """
        idx = self.ix(word)
        return self.vectors[idx]

    def cosine(self, word, n=10):
        """
        Cosine similarity.

        metric = dot(vectors_of_vectors, vectors_of_target_vector)
        Uses a precomputed vectors of the vectors

        Parameters
        ----------
        word : string
        n : int, optional (default 10)
            number of neighbors to return

        Returns
        -------
        2 numpy.array:
            1. position in self.vocab
            2. cosine similarity
        """
        metrics = np.dot(self.vectors, self[word].T)
        best = np.argsort(metrics)[::-1][1:n+1]
        best_metrics = metrics[best]
        return best, best_metrics

    def cosine_vec(self, vec, n=10):
        """
        Cosine similarity.

        metric = dot(vectors_of_vectors, vectors_of_target_vector)
        Uses a precomputed vectors of the vectors

        Parameters
        ----------
        word : string
        n : int, optional (default 10)
            number of neighbors to return

        Returns
        -------
        2 numpy.array:
            1. position in self.vocab
            2. cosine similarity
        """
        metrics = np.dot(self.vectors, vec.T)
        best = np.argsort(metrics)[::-1][1:n+1]
        best_metrics = metrics[best]
        return best, best_metrics
    
    
    def analogy(self, pos, neg, n=10):
        """
        Analogy similarity.

        Parameters
        ----------
        pos : list
        neg : list

        Returns
        -------
        2 numpy.array:
            1. position in self.vocab
            2. cosine similarity

        Example
        -------
            `king - man + woman = queen` will be:
            `pos=['king', 'woman'], neg=['man']`
        """
        exclude = pos + neg
        pos = [(word, 1.0) for word in pos]
        neg = [(word, -1.0) for word in neg]

        mean = []
        for word, direction in pos + neg:
            mean.append(direction * self[word])
        mean = np.array(mean).mean(axis=0)

        metrics = np.dot(self.vectors, mean)
        best = metrics.argsort()[::-1][:n + len(exclude)]

        exclude_idx = [np.where(best == self.ix(word)) for word in exclude if
                       self.ix(word) in best]
        new_best = np.delete(best, exclude_idx)
        best_metrics = metrics[new_best]
        return new_best[:n], best_metrics[:n]

    def generate_response(self, indexes, metrics, clusters=True):
        '''
        Generates a pure python (no numpy) response based on numpy arrays
        returned by `self.cosine` and `self.analogy`
        '''
        if self.clusters and clusters:
            return np.rec.fromarrays((self.vocab[indexes], metrics,
                                     self.clusters.clusters[indexes]),
                                     names=('word', 'metric', 'cluster'))
        else:
            return np.rec.fromarrays((self.vocab[indexes], metrics),
                                     names=('word', 'metric'))

    def to_mmap(self, fname):
        if not joblib:
            raise Exception("sklearn is needed to save as mmap")

        joblib.dump(self, fname)
    
    @staticmethod
    def read_hidden_layer(fname):
        """
        Read hidden layers
        """
        fsyn1 = fname + ".syn1"
        if not os.path.isfile(fsyn1):
            return None

        model = {}
        with open(fsyn1, 'r') as f:
            header = f.readline()
            tokens = header.strip().split()
            for idx in range(0, len(tokens), 2):
                model[tokens[idx]] = int(tokens[idx+1])
            
            syn1 = {}
            for i, line in enumerate(f):
                tokens = line.strip().split(' ')
                key =  tokens[0]
                vector = np.array(tokens[1:], dtype=np.float)
                syn1[key] = vector

            model['syn1'] = syn1
            
        if model['hs']:
            fvocab = fname + ".vocab"
            if not os.path.isfile(fvocab):
                return None
            vocab = {}
            with open(fvocab, 'r') as f:
                for line in f:
                    tokens  = line.strip().split(' ')
                    ventry = {}
                    ventry['word'] = tokens[0]
                    ventry['codelen'] = int(tokens[1])
                    point = []
                    code = []
                    for idx in xrange(ventry['codelen']):
                        point.append(tokens[2+idx])
                        code.append(int(tokens[2+ventry['codelen']+idx]))

                    ventry['point'] = point
                    ventry['code'] = code
                    vocab[ventry['word']] = ventry

            model['vocab'] = vocab
        else:
            model['vocab'] = None

        return model

    @classmethod
    def from_binary(cls, fname, vocabUnicodeSize=78, desired_vocab=None):
        """
        Create a WordVectors class based on a word2vec binary file

        Parameters
        ----------
        fname : path to file
        vocabUnicodeSize: the maximum string length (78, by default)
        desired_vocab: if set, this will ignore any word and vector that
                       doesn't fall inside desired_vocab.

        Returns
        -------
        WordVectors instance
        """
        train = cls.read_hidden_layer(fname)
        with open(fname, 'rb') as fin:
            header = fin.readline()
            vocab_size, vector_size = list(map(int, header.split()))

            vocab = np.empty(vocab_size, dtype='<U%s' % vocabUnicodeSize)
            vectors = np.empty((vocab_size, vector_size), dtype=np.float)
            binary_len = np.dtype(np.float32).itemsize * vector_size
            for i in range(vocab_size):
                # read word
                word = ''
                while True:
                    ch = fin.read(1).decode('ISO-8859-1')
                    if ch == ' ':
                        break
                    word += ch
                include = desired_vocab is None or word in desired_vocab
                if include:
                    vocab[i] = word

                # read vector
                vector = np.fromstring(fin.read(binary_len), dtype=np.float32)
                if include:
                    vectors[i] = unitvec(vector)
                fin.read(1)  # newline

            if desired_vocab is not None:
                vectors = vectors[vocab != '', :]
                vocab = vocab[vocab != '']
        # train = cls.read_hidden_layer(fname)
        return cls(vocab=vocab, vectors=vectors, train=train)

    @classmethod
    def from_text(cls, fname, vocabUnicodeSize=78, desired_vocab=None):
        """
        Create a WordVectors class based on a word2vec text file

        Parameters
        ----------
        fname : path to file
        vocabUnicodeSize: the maximum string length (78, by default)
        desired_vocab: if set, this will ignore any word and vector that
                       doesn't fall inside desired_vocab.

        Returns
        -------
        WordVectors instance
        """
        with open(fname, 'rb') as fin:
            header = fin.readline()
            vocab_size, vector_size = list(map(int, header.split()))

            vocab = np.empty(vocab_size, dtype='<U%s' % vocabUnicodeSize)
            vectors = np.empty((vocab_size, vector_size), dtype=np.float)
            for i, line in enumerate(fin):
                line = line.decode('ISO-8859-1').strip()
                parts = line.split(' ')
                word = parts[0]
                include = desired_vocab is None or word in desired_vocab
                if include:
                    vector = np.array(parts[1:], dtype=np.float)
                    vocab[i] = word
                    vectors[i] = unitvec(vector)

            if desired_vocab is not None:
                vectors = vectors[vocab != '', :]
                vocab = vocab[vocab != '']
        
        train = cls.read_hidden_layer(fname)
        return cls(vocab=vocab, vectors=vectors, train=train)
    


    @classmethod
    def from_mmap(cls, fname):
        """
        Create a WordVectors class from a memory map

        Parameters
        ----------
        fname : path to file

        Returns
        -------
        WordVectors instance
        """
        memmaped = joblib.load(fname, mmap_mode='r+')
        train = cls.read_hidden_layer(fname)
        return cls(vocab=memmaped.vocab, vectors=memmaped.vectors, train=train)
