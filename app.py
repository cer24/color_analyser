import streamlit as st
import pymongo
from pymongo import MongoClient
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans
import numpy as np
import clipboard
import matplotlib.pyplot as plt
import time

# Connect to the MongoDB database
client = MongoClient("mongodb+srv://shruti:tbhl1234@atlascluster.iukavux.mongodb.net/?retryWrites=true&w=majority")
db = client.color_db
users = db.users
collection = db.palette




def app():
    # Connect to the users collection
    users = db.users
    st.session_state.hex_codes = []


    # Authentication function
    def authenticate(username, password):
        user = users.find_one({"username": username})
        if user and user["password"] == password:
            return True
        else:
            return False

    # Registration function
    def register(username, password):
        user = users.find_one({"username": username})
        if user is None:
            users.insert_one({"username": username, "password": password})
            return True
        else:
            return False

    # Logout function
    def logout():
        st.session_state.pop("authenticated")
        st.success("You have been logged out")

    # Set page title and description
    st.set_page_config(page_title="Color Analyzer", page_icon=":art:", layout="wide")

    # Define the sidebar
    st.sidebar.title("Color Analyzer")
    st.sidebar.header("Login or Create Account")
    #st.sidebar.tabs([""])
    

    # Check if the user is logged in and display the logout button
    if st.session_state.get("authenticated"):
        st.sidebar.tabs([" "])
        st.sidebar.button("Logout", on_click=logout)
        st.sidebar.divider()
        if st.sidebar.button("Save Colors"):
            save_to_db(st.session_state.hex_codes)
        st.sidebar.button("View Saved Palettes", on_click=display_saved_palettes)
        # Run color analysis page
        color_analysis()
    else:
        # Define the horizontal tabs
        tabs = ["Login", "Create Account"]
        active_tab = st.sidebar.radio("Select Option", tabs,horizontal=True)

        if active_tab == "Login":
            st.sidebar.subheader("Login")
            username = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type="password")

            if st.sidebar.button("Login"):
                if authenticate(username, password):
                    st.session_state.authenticated = True
                    st.success("You are now logged in as {}".format(username))
                    # Run color analysis page
                    color_analysis()
                else:
                    st.error("Invalid username or password")
            st.image("login.png",width=600)

        elif active_tab == "Create Account":
            st.sidebar.subheader("Create a new account")
            new_username = st.sidebar.text_input("Username")
            new_password = st.sidebar.text_input("Password", type="password")
            confirm_password = st.sidebar.text_input("Confirm Password", type="password")

            if st.sidebar.button("Register"):
                if new_password == confirm_password:
                    if register(new_username, new_password):
                        st.balloons()
                        st.success("Account created for {}".format(new_username))
                        st.write("Click on Login to sign in!")
                    else:
                        st.sidebar.error("Username already taken")
                else:
                    st.sidebar.error("Passwords do not match")
            st.image("signup.png",width=600)




def save_to_db(hex_codes):
        # Check if the user is logged in
        if not st.session_state.get("authenticated"):
            st.error("You need to be logged in to save color palettes")
            return

        # Get the logged-in user's username
        username = st.session_state.get("authenticated")

        # Create a document with the color palette data
        palette_doc = {
            "username": username,
            "hex_codes": hex_codes,
            "created_at": time.time()
        }

        # Insert the document into the palette collection
        collection.insert_one(palette_doc)

        st.success("Color palette saved to your account")



    # Display user's saved color palettes
# Display user's saved color palettes
def display_saved_palettes():
    # Check if the user is logged in
    if not st.session_state.get("authenticated"):
        st.error("You need to be logged in to view saved color palettes")
        return

    # Get the logged-in user's username
    username = st.session_state.get("authenticated")

    # Retrieve the user's saved color palettes from the palette collection
    palettes = collection.find({"username": username})
    
    # Display each color palette
    #with st.expander("Saved Color Palettes"):
    st.write("Your saved color palettes:")
    for palette in palettes:
        hex_codes = palette["hex_codes"]
        st.write("Palette:")
        col_count = len(hex_codes)
        cols = st.columns(max(len(hex_codes), 1))
        for i, hex_code in enumerate(hex_codes):
            with cols[i]:
                color_box = f'<div style="background-color:{hex_code}; width:100px; height:50px;"></div>'
                st.markdown(color_box, unsafe_allow_html=True)
                st.write(hex_code)


def copy_to_clipboard(hex_code):
    pyperclip.copy(hex_code)
    print(f"Copied {hex_code} to clipboard")


def color_analysis():
        
            st.title("Color Analyzer")
            st.subheader("Settings")

            # Create file uploader
            uploaded_file = st.file_uploader("Select an image")

            # Create number of clusters input
            n_clusters = st.number_input("Number of clusters", min_value=1, value=3)

            # Create run button
            run_button = st.button("Run Clustering")



            if uploaded_file is not None:
                # Display uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded image", use_column_width=True)


            # Run clustering algorithm
            if run_button:
                if uploaded_file is None:
                    st.error("Please select an image")
                    return

                
                with st.spinner("Running clustering..."):   
                    # Load image and convert to numpy array
                    image = Image.open(uploaded_file)
                    orig_width, orig_height = image.size
                    new_height = 300
                    new_width = int(orig_width / orig_height * new_height)
                    image_array = np.array(image.resize((new_width, new_height)))

                    # Reshape the array to a 2D matrix of pixels
                    width, height, depth = image_array.shape
                    pixel_matrix = image_array.reshape(width * height, depth)

                    # Run KMeans algorithm
                    kmeans = KMeans(n_clusters=n_clusters)
                    kmeans.fit(pixel_matrix)

                    # Replace each pixel with its corresponding cluster center
                    new_image_array = np.zeros_like(pixel_matrix)
                    hex_codes = []
                    color_counts = []
                    for i, cluster_label in enumerate(kmeans.labels_):
                        new_image_array[i] = kmeans.cluster_centers_[cluster_label]
                        hex_code = "#%02x%02x%02x" % tuple(map(int, kmeans.cluster_centers_[cluster_label]))
                        if hex_code not in hex_codes:
                            hex_codes.append(hex_code)
                            color_counts.append(1)
                        else:
                            index = hex_codes.index(hex_code)
                            color_counts[index] += 1

                    # Create a new image with the computed colors
                    new_image_array = new_image_array.reshape(width, height, depth)
                    image = Image.fromarray(np.uint8(new_image_array))

                    # Display original and new images side by side
                    col1, col2 = st.columns(2)
                    with col1:
                        st.image(Image.open(uploaded_file), caption="Original Image", use_column_width=True)
                    with col2:
                        st.image(image, caption=f"{n_clusters} Cluster(s)", use_column_width=True)

                    # Create palette image
                    palette_size = 50
                    palette_image = Image.new("RGB", (palette_size * n_clusters, palette_size), (255, 255, 255))

                    # Draw color squares on palette image
                    draw = ImageDraw.Draw(palette_image)
                    x_offset = 0
                    for i, hex_code in enumerate(hex_codes):
                        r, g, b = tuple(int(hex_code[i:i + 2], 16) for i in (1, 3, 5))
                        draw.rectangle([(x_offset, 0), (x_offset + palette_size, palette_size)], fill=(r, g, b))
                        x_offset += palette_size

                    # Display palette image
                    st.image(palette_image, caption="Color Palette", use_column_width=True)

                    
                    # Display hex codes and colors
                    st.write("Colors:")
                    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 5))
                    colors = []
                    labels = []
                    sizes = []
                    for i, hex_code in enumerate(hex_codes):
                        colors.append(hex_code)
                        labels.append(hex_code)
                        sizes.append(color_counts[i])
                        col1, col2, col3, col4 = st.columns([1, 2, 3, 2])
                        with col1:
                            color_image = Image.new("RGB", (50, 50), hex_code)
                            color_image = color_image.resize((60, 30))
                            st.image(color_image)
                        with col2:
                            st.write(hex_code)
                        with col3:
                            st.write(f"Count: {color_counts[i]}")
                        with col4:
                            st.button(
                                f"Copy to clipboard",
                                key=hex_code,
                                on_click=copy_to_clipboard(hex_code)
                            )
                    # Create a file to save the hex codes
                    with open("hex_codes.txt", "w") as file:
                        for hex_code in hex_codes:
                            file.write(hex_code + "\n")

                    # Create the "Save Hex Codes" button in the sidebar
                    st.sidebar.download_button(
                        label="Download Hex Codes",
                        data="hex_codes.txt",
                        file_name="hex_codes.txt",
                        mime="text/plain"
                    )

                    #st.button("Save Colors", on_click=save_to_db(hex_codes))
                    # Save the hex codes to a file and store to MongoDB


                    with st.spinner("Generating color distribution chart..."):
                        # Display pie chart of color distribution
                        fig, ax = plt.subplots()
                        ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", textprops={"fontsize": 5})
                        st.write("Color Distribution:")
                        st.pyplot(fig)

                    with st.spinner("Generating color count chart..."):
                        # Create bar chart of color counts
                        fig, ax = plt.subplots()
                        ax.bar(hex_codes, color_counts, color=hex_codes)
                        plt.xticks(rotation=45)
                        plt.xlabel("Hex Codes")
                        plt.ylabel("Count")
                        plt.title("Color Counts")
                        st.write("Color Counts:")
                        st.pyplot(fig)


if __name__ == "__main__":
    app()
