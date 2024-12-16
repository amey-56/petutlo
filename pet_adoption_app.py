import os
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
from PIL import Image
import bcrypt

# Streamlit page configuration
st.set_page_config(page_title="Pet Adoption Platform 🐾", layout="wide")

# Initialize Firebase using Streamlit secrets
if not firebase_admin._apps:
    try:
        firebase_secrets = st.secrets["firebase"]
        cred = credentials.Certificate({
            "type": firebase_secrets["type"],
            "project_id": firebase_secrets["project_id"],
            "private_key_id": firebase_secrets["private_key_id"],
            "private_key": firebase_secrets["private_key"].replace("\\n", "\n"),
            "client_email": firebase_secrets["client_email"],
            "client_id": firebase_secrets["client_id"],
            "auth_uri": firebase_secrets["auth_uri"],
            "token_uri": firebase_secrets["token_uri"],
            "auth_provider_x509_cert_url": firebase_secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": firebase_secrets["client_x509_cert_url"],
        })
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://pet-pro-d4c5f-default-rtdb.firebaseio.com/"
        })
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")

# Initialize session state
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None

# Helper Functions
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def save_image(uploaded_file, filename):
    try:
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
        file_path = os.path.join("uploads", filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving image: {e}")
        return None

def embed_map(location):
    """Embed Google Maps for the given location."""
    if location:
        st.markdown(
            f"""
            <iframe
                width="100%"
                height="300"
                style="border:0"
                loading="lazy"
                allowfullscreen
                src="https://www.google.com/maps/embed/v1/place?key=AIzaSyAHGImzRjI4lacl54UpAg_I2YxwbR2Y4_Y&q={location}">
            </iframe>
            """,
            unsafe_allow_html=True
        )

def add_comment(pet_id, comment_text):
    """Add a comment to a specific pet."""
    if st.session_state.get("logged_in_user"):
        comments_ref = db.reference(f"comments/{pet_id}")
        commenter = st.session_state["logged_in_user"]["username"]
        comments_ref.push({"commenter": commenter, "text": comment_text})
    else:
        st.error("You must be logged in to add a comment!")

def view_comments(pet_id):
    """Display comments for a specific pet."""
    comments_ref = db.reference(f"comments/{pet_id}").get()
    st.write("💬 **Comments:**")
    if comments_ref:
        for comment in comments_ref.values():
            st.write(f"🔸 **{comment['commenter']}:** {comment['text']}")
    else:
        st.write("🗨️ No comments yet. Be the first to comment!")

def mark_as_adopted(pet_id):
    """Mark a pet as adopted."""
    try:
        db.reference(f"pets/{pet_id}").update({"adopted": True})
        st.success("🎉 Pet marked as adopted!")
    except Exception as e:
        st.error(f"Failed to mark pet as adopted: {e}")

# Authentication
def register():
    st.sidebar.subheader("🚀 Register")
    with st.sidebar.form("register_form"):
        full_name = st.text_input("✨ Full Name")
        username = st.text_input("🔑 Username")
        password = st.text_input("🔒 Password", type="password")
        submit = st.form_submit_button("🎉 Register")

        if submit:
            users_ref = db.reference("users")
            if users_ref.child(username).get():
                st.sidebar.error("❌ Username already exists!")
            else:
                hashed_password = hash_password(password)
                users_ref.child(username).set({"full_name": full_name, "password": hashed_password})
                st.sidebar.success("🎊 Registration successful! Please log in.")

def login():
    st.sidebar.subheader("🔓 Login")
    username = st.sidebar.text_input("🔑 Username")
    password = st.sidebar.text_input("🔒 Password", type="password")

    if st.sidebar.button("🚪 Log In"):
        # Validate user credentials
        try:
            user_ref = db.reference(f"users/{username}").get()
            if user_ref and verify_password(password, user_ref["password"]):
                # Update session state with logged-in user
                st.session_state["logged_in_user"] = {
                    "username": username,
                    "full_name": user_ref["full_name"]
                }
                st.sidebar.success(f"🎉 Welcome, {user_ref['full_name']}!")
            else:
                st.sidebar.error("❌ Invalid credentials!")
        except Exception as e:
            st.sidebar.error(f"Error logging in: {e}")

def logout():
    st.session_state["logged_in_user"] = None
    st.experimental_set_query_params()  # Redirect to the same app to refresh the state
    st.sidebar.success("Logged out successfully!")

# Pet Management
def add_pet():
    st.subheader("🐾 Add Your Pet")
    with st.form("add_pet_form", clear_on_submit=True):
        name = st.text_input("🐶 Pet's Name")
        pet_type = st.selectbox("🦄 Type of Pet", ["Dog", "Cat", "Bird", "Other"])
        age = st.number_input("🎂 Age (in years)", min_value=0.0, step=0.1)
        description = st.text_area("📜 Description")
        location = st.text_input("📍 Location (City/Address)")
        vaccinated = st.radio("💉 Vaccinated?", ["Yes", "No"])
        images = st.file_uploader("📸 Upload up to 3 Pictures", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        submit = st.form_submit_button("➕ Add Pet")

        if submit:
            image_paths = []
            for i, image in enumerate(images[:3]):  # Limit to 3 images
                filename = f"{name.lower().replace(' ', '_')}_img{i+1}.jpg"
                image_path = save_image(image, filename)
                if image_path:
                    image_paths.append(image_path)
            
            pet_data = {
                "name": name,
                "pet_type": pet_type,
                "age": age,
                "description": description,
                "location": location,
                "vaccinated": vaccinated,
                "image_paths": image_paths,
                "adopted": False,
                "owner": st.session_state["logged_in_user"]["username"]
            }
            try:
                db.reference("pets").push(pet_data)
                st.success(f"🎉 Pet '{name}' added successfully!")
            except Exception as e:
                st.error(f"Failed to add pet: {e}")

def view_pets(show_my_pets=False):
    """View all pets or only the logged-in user's pets."""
    st.subheader("🐕 Available Pets" if not show_my_pets else "🐾 My Pets")
    pets_ref = db.reference("pets").get()
    if not pets_ref:
        st.write("❌ No pets available!")
        return

    for pet_id, pet in pets_ref.items():
        if show_my_pets and pet.get("owner") != st.session_state["logged_in_user"]["username"]:
            continue
        if not show_my_pets and pet.get("adopted"):
            continue
        
        st.write(f"**{pet.get('name')} ({pet.get('pet_type')}) - {pet.get('age')} years**")
        st.write(f"📜 {pet.get('description')}")
        st.write(f"📍 Location: {pet.get('location')}")
        embed_map(pet.get("location"))
        if pet.get("image_paths"):
            for img_path in pet["image_paths"]:
                st.image(img_path, caption=pet.get("name"), use_column_width=True)
        view_comments(pet_id)
        if pet.get("owner") == st.session_state["logged_in_user"]["username"] and not pet.get("adopted"):
            if st.button(f"Mark '{pet.get('name')}' as Adopted", key=f"adopt_{pet_id}"):
                mark_as_adopted(pet_id)
        comment_text = st.text_input(f"Add a comment for {pet.get('name')}", key=f"comment_{pet_id}")
        if st.button(f"Comment on {pet.get('name')}", key=f"button_{pet_id}"):
            add_comment(pet_id, comment_text)

# Main Application
def landing_page():
    st.markdown("""
    <style>
        .landing-container { text-align: center; margin-top: 50px; }
        .title { font-size: 60px; color: #FF6F61; font-weight: bold; }
        .subtitle { font-size: 22px; color: #666; }
    </style>
    <div class="landing-container">
        <h1 class="title">🐾 Welcome to PetAdopt 🐾</h1>
        <p class="subtitle">Find your new furry friend today!</p>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.title("🚀 Navigation")

if st.session_state["logged_in_user"] is None:
    landing_page()
    login()
    register()
else:
    user = st.session_state["logged_in_user"]
    st.sidebar.write(f"👋 Logged in as: **{user['full_name']}**")
    page = st.sidebar.radio("Go to", ["🏠 Home", "➕ Add a Pet", "🐾 My Pets", "🚪 Logout"])

    if page == "🏠 Home":
        view_pets()
    elif page == "➕ Add a Pet":
        add_pet()
    elif page == "🐾 My Pets":
        view_pets(show_my_pets=True)
    elif page == "🚪 Logout":
        logout()
