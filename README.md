# 🎵 Music-Recommendation-System

Welcome to the **Music-Recommendation-System**! This project leverages the Spotify API to provide intelligent and personalized music recommendations. Built with Python and Gradio, it offers a sleek interface for users to discover new music tailored to their tastes.

---

## 📖 Introduction

The **Music-Recommendation-System** helps users find their next favorite song or artist by analyzing preferences and suggesting tracks using Spotify's powerful recommendation engine. With a user-friendly web interface, you can instantly get curated playlists based on your mood, genre, or current favorites.

---

## ✨ Features

- 🔑 **OAuth2 Authentication** with Spotify
- 🎶 **Personalized Music Recommendations**
- 💻 **Interactive Web Interface** using Gradio
- 🔄 **Automatic Token Refreshing**
- 🗂️ **Environment Variable Support** for secure configuration
- ⚡ **Cross-platform & Easy to Use**

---

## 🚀 Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/Music-Recommendation-System.git
   cd Music-Recommendation-System
   ```

2. **Create a virtual environment (optional but recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your environment variables:**

   Create a `.env` file in the project root with the following content:

   ```env
   CLIENT_ID=your_spotify_client_id
   CLIENT_SECRET=your_spotify_client_secret
   REDIRECT_URI=http://localhost:your_port/callback
   ```

   Replace the placeholders with your actual Spotify API credentials.

---

## 🕹 Usage

1. **Start the application:**

   ```bash
   python app.py
   ```

2. **Authenticate with Spotify:**  
   The app will guide you through logging in to your Spotify account for personalized recommendations.

3. **Get Recommendations:**  
   Use the web interface to input your favorite songs, artists, or genres and receive customized music suggestions.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please consult the [CONTRIBUTING.md](CONTRIBUTING.md) (if available) for more details.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

Enjoy discovering new music! 🎧

## License
This project is licensed under the **MIT** License.

---
🔗 GitHub Repo: https://github.com/selvaganesh19/Music-Recommendation-System
