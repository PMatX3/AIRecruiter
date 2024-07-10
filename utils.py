import os
from openai import OpenAI
from mongo_connection import get_mongo_client
from PyPDF2 import PdfReader
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import uuid
import google.generativeai as genai

# Load environment variables
load_dotenv()

mongo_client = get_mongo_client()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_API_KEY,
                model_name="text-embedding-3-small"
            )
client = chromadb.Client()
collection = client.get_or_create_collection("resumes",embedding_function=openai_ef)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

model = genai.GenerativeModel('gemini-1.5-flash')

genai.configure(api_key=GEMINI_API_KEY) 

def generate_embedding(text, temp=False):
    response = openai_client.embeddings.create(model="text-embedding-3-small", input=text)
    embedding = response.data[0].embedding
    if not temp:
        # Generate a unique ID for the document using uuid4
        document_id = str(uuid.uuid4())
        collection.add(documents=[text], ids=[document_id])
        print('added to db')
    return embedding

def extract_text_from_pdf(file):
    pdf_reader = PdfReader(file)
    text = ''
    for page in pdf_reader.pages:
        extracted_text = page.extract_text()
        if extracted_text:
            text += extracted_text
    return text

def save_resumes_embedding():
    resume_dir = 'resumes/'
    for filename in os.listdir(resume_dir):
        if filename.endswith('.pdf'):
            file_path = os.path.join(resume_dir, filename)
            text = extract_text_from_pdf(file_path)
            embedding = generate_embedding(text)
            print(f"Embedding for {filename} saved.")

def get_results(query, job_info_json):
    embedding = generate_embedding('give me top 10 candidates', temp=True)
    
    resumes = collection.query(query_embeddings=embedding, n_results=10000, include=["documents"])
    prompt = f"""
    Here are the job description:
    {job_info_json}
    Here are the resumes:
    {resumes['documents'][0]} based on above data answer the question clearly and answer in a structured way
    """

    messages = [
        # {"role": "model", "parts": "Welcome to Recruiter AI Bot! I'm here to assist you by providing structured answers to your questions based on the job descriptions and query , ensuring there are no repetitions and it is beautifully formatted. I'll make sure that the answer matches the query and If I don't know the answer, I'll never give you the wrong answer. Let's get started! If you have any questions, feel free to ask."},
        {"role": "model", "parts": f"Recruiters are like treasure hunters, but instead of finding gold, they find the best people to work in a company. They talk to a lot of people, look at their skills, and decide who would be the best fit for different jobs. It's like picking the best players for a team to make sure everyone has fun and does a great job! {prompt}"},
        {"role": "user", "parts": query}
    ]

    response = model.generate_content(messages)

    return response.text

def combine_resumes():
    import PyPDF2
    import os

    # Directory containing the resumes
    resume_dir = 'best_resumes/'
    
    # Create a PDF merger object
    merger = PyPDF2.PdfMerger()

    # Iterate through all PDF files in the directory
    for filename in os.listdir(resume_dir):
        if filename.endswith('.pdf'):
            filepath = os.path.join(resume_dir, filename)
            # Append the PDF to the merger
            merger.append(filepath)

    # Write the combined PDF to a file
    output_path = os.path.join(resume_dir, 'combined_resumes.pdf')
    merger.write(output_path)
    merger.close()

    print(f"All resumes have been combined into {output_path}")
