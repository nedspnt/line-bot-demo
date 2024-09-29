import os
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema import HumanMessage, AIMessage

# load environment varaibles from .env file
load_dotenv()

# load context text file
loader = TextLoader("data/unrealistic_animals.txt")
documents = loader.load()

# split doc into chucks
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = text_splitter.split_documents(documents)

# embed into vector store
embeddings = OpenAIEmbeddings(api_key=os.getenv('OPENAI_API_KEY_LINE'))
vectorstore = FAISS.from_documents(docs, embeddings)

# conversation memory
memory = ConversationBufferMemory(memory_key="001", return_messages=True)

# init LLM
llm = ChatOpenAI(temperature=0, openai_api_key=os.getenv('OPENAI_API_KEY_LINE'))

# retriever
retriever = vectorstore.as_retriever()

def reply_conversation(input_message):
    prompt_search_query = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="chat_history"),
            ("user","{input}"),
            ("user","Given the above conversation, generate a search query to look up to get information relevant to the conversation")
        ]
    )
    prompt_get_answer = ChatPromptTemplate.from_messages(
        [
            ("system", "Answer the user's questions based on the below context:\\n\\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user","{input}"),
        ]
    )
    
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, prompt_search_query
    )

    question_answer_chain = create_stuff_documents_chain(llm, prompt_get_answer)

    rag_chain = create_retrieval_chain(
        history_aware_retriever, question_answer_chain
    )

    chat_history = memory.load_memory_variables({})["001"]

    for chat in chat_history:
        print(chat)
    
    reply = rag_chain.invoke({
        "chat_history": chat_history,
        "input": input_message
    })

    memory.chat_memory.add_user_message(input_message)

    print(chat_history)

    return reply["answer"]