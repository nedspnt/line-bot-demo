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
from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory

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

# session history
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

def reply_conversation_with_session_id(input_message, session_id, model=llm):

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a supportive and loving man named Jason. You are dating with her and get to know her, not assist her in any way.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    chain = prompt | model

    with_message_history = RunnableWithMessageHistory(chain, get_session_history, input_messages_key="messages")

    response = with_message_history.invoke(
        {"messages": [HumanMessage(content=input_message)], "language": "English"},
        config={"configurable": {"session_id": session_id}},
    )

    return response.content

def reply_conversation_with_context(input_message, llm=llm, memory=memory, context_vectorstore=vectorstore):

    context_retriever = context_vectorstore.as_retriever()

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
        llm, context_retriever, prompt_search_query
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

    memory.save_context({"input": input_message}, {"response": reply["answer"]})

    return reply["answer"]
 