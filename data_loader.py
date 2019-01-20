import csv
from os.path import isfile
from preprocessing import Preprocessor
from utils import timeit
from word2vecReader import Word2Vec, Word2VecMini
import numpy as np

EMOTION_CLASSES = ["happiness", "anger", "sadness", "neutral"]


class DataLoader:
    @staticmethod
    def load_crowdflower_db(path):
        """
        Loads CrowdFlower database. Database contains of 14 classes:
        worry, enthusiasm, sadness, love, anger, surprise, relief, sentiment, happiness, fun, boredom, hate, neutral

        HAPPINESS:  enthusiasm, happiness, fun
        ANGER:      anger, hate
        SADNESS:    sadness
        NEUTRAL:    neutral

        :param path: path to database
        :return: Dataset object"""

        emotion_map = {"enthusiasm": "happiness", "happiness": "happiness", "fun": "happiness",
                       "sadness": "sadness", "anger": "anger","hate": "anger", "neutral": "neutral"}

        dataset = {class_name: [] for class_name in EMOTION_CLASSES}
        with open(path, 'r') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
            for i, row in enumerate(spamreader):
                # row is a list of 4 elements: tweet_id, emotion, user, content(may be seperated if contains ",")
                emotion = row[1]
                emotion = emotion.strip("\"")
                content = ",".join(row[3:])
                content = content.strip("\"")
                content = preprocess(content)
                # import pdb;pdb.set_trace()
                if emotion in emotion_map.keys():
                    dataset[emotion_map[emotion]].append(content)
        return dataset

    @staticmethod

    def load_sentiment_140(path):
        positive = []
        negative = []
        with open(path, 'r', encoding='latin-1') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',', quotechar="\n")
            for i, row in enumerate(csvreader):
                # row is a list of 4 elements: tweet_id, emotion, user, content(may be seperated if contains ",")
                sentiment = row[0].strip("\"").strip("\'")
                tweet = ",".join(row[5:])

                if int(sentiment) == 0:
                    negative.append(tweet)
                else:
                    positive.append(tweet)
        return positive, negative

    @staticmethod
    def load_data_from_txt():
        if isfile("data/positives.txt") and isfile("data/negatives.txt"):
            print("Loading cached positive & negative data")
            """Dumping preprocessed results"""
            with open("data/negatives.txt", 'r', encoding='latin-1') as negatives_file:
                negatives = negatives_file.read().split("\n")

            with open("data/positives.txt", 'r', encoding='latin-1') as positives_file:
                positives = positives_file.read().split("\n")
        else:
            print("Loading raw sentiment140 tweet data and running preprocessing")
            positives, negatives = DataLoader.load_sentiment_140(
                "/home/piotrsobczak/magisterka-dane/training.1600000.processed.noemoticon.csv")

            """Preprocessing"""
            positives = Preprocessor.preprocess_many(positives)
            negatives = Preprocessor.preprocess_many(negatives)

            """Dumping preprocessed results"""
            with open("data/negatives.txt", 'w', encoding='latin-1') as negatives_file:
                negatives_file.write("\n".join(negatives))

            with open("data/positives.txt", 'w', encoding='latin-1') as positives_file:
                positives_file.write("\n".join(positives))

            # print(max(Preprocessor.sentence_len))
            # print(sum(Preprocessor.sentence_len)/len(Preprocessor.sentence_len))

        return positives, negatives

    @staticmethod
    def get_data_in_batches():
        positives, negatives = DataLoader.load_data_from_txt()

        """Balancing positive& negative sampling after ignoring some tweets based on sequence length"""
        balanced_size = len(positives) if len(negatives) > len(positives) else len(negatives)
        positives = positives[:balanced_size]
        negatives = negatives[:balanced_size]

        print("Loaded data.{} positives and {} negatives".format(len(positives), len(negatives)))

        batch_list = []
        BATCH_SIZE = 64
        BATCH_SIZE_HALF = int(BATCH_SIZE / 2)
        NUM_BATCHES = int((len(positives) + len(negatives)) / BATCH_SIZE)

        for i in range(NUM_BATCHES):
            # batch_input = np.zeros((BATCH_SIZE, 400))
            batch_input = positives[i * BATCH_SIZE_HALF:i * BATCH_SIZE_HALF + BATCH_SIZE_HALF]
            batch_input += negatives[i * BATCH_SIZE_HALF:i * BATCH_SIZE_HALF + BATCH_SIZE_HALF]
            batch_labels = [1] * BATCH_SIZE_HALF + [0] * BATCH_SIZE_HALF
            batch_list.append({"inputs": batch_input, "labels": batch_labels})

        TRAIN_BATCHES = 190
        VAL_BATCHES = 3000
        TEST_BATCHES = 3000

        train = batch_list[:TRAIN_BATCHES]
        val = batch_list[TRAIN_BATCHES: TRAIN_BATCHES + VAL_BATCHES]
        test = batch_list[TRAIN_BATCHES + VAL_BATCHES:]

        print("Loaded data. Number of batches: {}".format(NUM_BATCHES))
        print("Train set size: {}.".format(len(train)))
        print("Val set size: {}.".format(len(val)))
        print("Test set size: {}.".format(len(test)))

        return train, val, test


class BatchLoader:
    def __init__(self, raw_batch_list, sequence_len=30, batch_size=64, embedding_size=400):
        self._raw_batch_list = raw_batch_list
        self._size = len(raw_batch_list)
        self._next_batch_index = 0
        self._batch_size = batch_size
        self._embedding_size = embedding_size
        self._sequence_len = sequence_len

    @property
    def size(self):
        return self._size

    def next(self):
        raw_batch = self._raw_batch_list[self._next_batch_index]
        self._next_batch_index = (self._next_batch_index + 1) if self._next_batch_index + 1 < self._size else 0
        return self._create_batch(raw_batch)

    def _create_batch(self, raw_batch):
        batch = np.zeros((self._batch_size, self._sequence_len, self._embedding_size))
        for sentence_id, sentence in enumerate(raw_batch["inputs"]):
            words = sentence.split(" ")
            sentence_embedded = np.zeros((self._sequence_len, self._embedding_size))
            for word_id in range(self._sequence_len):
                if word_id < len(words):
                    sentence_embedded[word_id] = Word2VecMini.get_embedding(words[word_id])
                # else:
                #     sentence_embedded[word_id] = np.zeros((1, self._embedding_size))
            batch[sentence_id] = sentence_embedded
        return batch.swapaxes(0,1), np.array(raw_batch["labels"])


if __name__ == "__main__":
    train, val, test = DataLoader.get_data_in_batches()
    train_loader = BatchLoader(train)
    batch = train_loader.next()
    import pdb;pdb.set_trace()


