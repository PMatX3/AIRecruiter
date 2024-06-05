import os
from openai import OpenAI
from mongo_connection import get_mongo_client
from PyPDF2 import PdfReader
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import uuid
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.footnote import footnote_plugin

# Load environment variables
load_dotenv()

mongo_client = get_mongo_client()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_API_KEY,
                model_name="text-embedding-3-small"
            )
client = chromadb.Client()
collection = client.get_or_create_collection("resumes",embedding_function=openai_ef)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

md = (
    MarkdownIt('commonmark' ,{'breaks':True,'html':True})
    .use(front_matter_plugin)
    .use(footnote_plugin)
    .enable('table')
)

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

def get_results(query):
    embedding = generate_embedding('give me top 10 candidates', temp=True)
    resumes = collection.query(query_embeddings=embedding, n_results=10000, include=["documents"])
    print(resumes['documents'][0])
    prompt = f"""
    Here are the resumes:
    {resumes['documents'][0]} answer the {query} based on resumes and return the emails of the resumes only
    """

    messages = [
        {"role": "system", "content": "Welcome to Recruiter AI Bot! I'm here to assist you by providing structured answers to your questions, ensuring there are no repetitions and it is beautifully formatted. Let's get started! If you have any questions, feel free to ask."},
        {"role": "user", "content": prompt}
    ]
    
    # Start streaming        
    print('Using chat completions for general query.')
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.1
    )

    res = response.choices[0].message.content

    rendered_response = md.render(res)

    return rendered_response