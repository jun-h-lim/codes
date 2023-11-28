import tkinter as tk
from tkinter import messagebox
import speech_recognition as sr
import re

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.count = 0
        self.score = 0

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word, score):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.count += 1
        node.score = ((node.score * (node.count - 1)) + score) / node.count

    def search(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                return None
            node = node.children[char]
        return node if node.is_end_of_word else None

    def save_to_file(self, file_path):
        with open(file_path, "w") as file:
            self._save_node(self.root, "", file)

    def _save_node(self, node, word, file):
        if node.is_end_of_word:
            file.write(f"{word} {node.count} {node.score:.2f}\n")
        for char, next_node in node.children.items():
            self._save_node(next_node, word + char, file)

    def load_from_file(self, file_path):
        try:
            with open(file_path, "r") as file:
                for line in file:
                    word, count, score = line.strip().split()
                    self.insert_existing(word, int(count), float(score))
        except FileNotFoundError:
            print(f"{file_path} 파일이 존재하지 않습니다. 새로운 파일을 생성합니다.")

    def insert_existing(self, word, count, score):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.count = count
        node.score = score

# Levenshtein Distance 알고리즘
def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def preprocess_text(text):
    # 정규 표현식을 사용하여 ., 등의 기호 제거
    return re.sub(r'[.,]', '', text)

# 문장을 단어 단위로 분리
def split_sentence(sentence):
    return preprocess_text(sentence).split()

# 음성 인식 함수
class VoiceApp:
    def __init__(self, window):
        self.window = window
        window.title("발음 교정 프로그램")
        window.geometry("300x400")

        # 입력 필드
        self.input_label = tk.Label(window, text="연습할 문장을 입력하세요")
        self.input_label.pack(anchor=tk.CENTER) # 가운데 정렬
        self.input_text = tk.Entry(window, width=50)
        self.input_text.pack(anchor=tk.CENTER)

        # 음성 인식 버튼
        self.recognize_btn = tk.Button(window, text="음성인식 시작", command=self.recognize_speech)
        self.recognize_btn.pack()

        # 상태 메시지 레이블
        self.status_label = tk.Label(window, text="")
        self.status_label.pack()

        # 결과 출력 영역
        self.result_label = tk.Label(window, text="결과")
        self.result_label.pack()
        self.result_text = tk.Text(window, width=50)
        self.result_text.pack()

        self.trie = Trie()
        self.trie.load_from_file("word_data.txt")

    def recognize_speech(self):
        self.status_label.config(text="듣고 있음...")
        self.window.update()   # 상태 메시지 업데이트
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()

        with microphone as source:
            audio = recognizer.listen(source)

        try:
            recognized_text = recognizer.recognize_google(audio, language='ko-KR')
            self.result_text.insert(tk.END, f"\t인식된 문장: {recognized_text}\n")
            self.process_text(recognized_text)
        except sr.UnknownValueError:
            self.result_text.insert(tk.END, "이해하지 못했습니다.\n")
        except sr.RequestError as e:
            self.result_text.insert(tk.END, f"Google Speech Recognition 서비스에 요청을 보낼 수 없습니다; {e}\n")
        
        self.status_label.config(text="")  # 상태 메시지 초기화
        self.window.update()  # 상태 레이블 업데이트 즉시 반영

    def process_text(self, recognized_text):
        input_sentence = self.input_text.get()  # 사용자가 입력한 문장 가져오기
        input_words = split_sentence(input_sentence)  # 입력 문장을 단어로 분리
        recognized_words = split_sentence(recognized_text)  # 인식된 문장을 단어로 분리

        # 가장 적합한 단어 매치 찾기
        matches = find_best_match(input_words, recognized_words)

        # 매치 결과 및 Trie 업데이트
        for input_word, recognized_word, distance in matches:
            max_length = max(len(input_word), len(recognized_word))
            score = (1 - (distance / max_length)) * 100 if max_length != 0 else 100
            self.result_text.insert(tk.END, f"\t입력 단어: {input_word}\n\t인식 단어: {recognized_word}\n\t점수: {score:.1f}\n")
            self.trie.insert(input_word, score)  # 사용자가 입력한 단어를 Trie에 저장

        # 변경된 Trie 데이터를 파일에 저장
        self.trie.save_to_file("word_data.txt")
    
def find_best_match(input_words, recognized_words):
    best_matches = []
    for input_word in input_words:
        best_match = None
        min_distance = float('inf')
        for recognized_word in recognized_words:
            distance = levenshtein_distance(input_word, recognized_word)
            if distance < min_distance:
                min_distance = distance
                best_match = recognized_word
        best_matches.append((input_word, best_match, min_distance))
    return best_matches

root = tk.Tk()
app = VoiceApp(root)
root.mainloop()