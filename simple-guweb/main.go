package main

import (
	"crypto/md5"
	"database/sql"
	"encoding/hex"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/go-sql-driver/mysql"
	"github.com/joho/godotenv"
	"golang.org/x/crypto/bcrypt"
)

var db *sql.DB

// --- STRUCTS ---

type User struct {
	ID           int
	Name         string
	SafeName     string
	Country      string
	Priv         int
	CreationTime int64
	LatestActivity int64
}

type Stats struct {
	Mode      int
	TScore    int64
	RScore    int64
	PP        int
	Plays     int
	PlayTime  int
	Acc       float64
	MaxCombo  int
	Rank      int // Global Rank (calculated)
}

type Score struct {
	ID         int64
	MapMD5     string
	Score      int
	PP         float64
	Acc        float64
	MaxCombo   int
	Mods       int
	Grade      string
	Mode       int
	PlayTime   string
	Date       string // Formatted date
	Beatmap    *Beatmap
}

type Beatmap struct {
	ID        int
	SetID     int
	Artist    string
	Title     string
	Version   string
	Creator   string
	Status    int
}

// --- DB INIT ---

func initDB() {
	// Load .env from parent directory if exists, or current
	_ = godotenv.Load("../.env")
	_ = godotenv.Load()

	dbUser := os.Getenv("DB_USER")
	if dbUser == "" { dbUser = "cmyui" }
	dbPass := os.Getenv("DB_PASS")
	if dbPass == "" { dbPass = "lol123" }
	dbName := os.Getenv("DB_NAME")
	if dbName == "" { dbName = "banchopy" }
	dbHost := "127.0.0.1" // Default to localhost since we are outside docker
	dbPort := os.Getenv("DB_PORT")
	if dbPort == "" { dbPort = "3306" }

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s", dbUser, dbPass, dbHost, dbPort, dbName)
	var err error
	db, err = sql.Open("mysql", dsn)
	if err != nil {
		log.Fatal(err)
	}

	if err := db.Ping(); err != nil {
		log.Fatal("Failed to connect to database: ", err)
	}
	log.Println("Connected to database successfully!")
}

// --- HANDLERS ---

func main() {
	initDB()

	r := gin.Default()
	
	// Load templates
	r.SetFuncMap(template.FuncMap{
		"formatDate": func(timestamp int64) string {
			return time.Unix(timestamp, 0).Format("2006-01-02 15:04")
		},
		"formatDuration": func(seconds int) string {
			d := time.Duration(seconds) * time.Second
			return d.String()
		},
		"getModeName": func(mode int) string {
			switch mode {
			case 0: return "Standard"
			case 1: return "Taiko"
			case 2: return "Catch"
			case 3: return "Mania"
			default: return "Unknown"
			}
		},
	})
	r.LoadHTMLGlob("templates/*")

	// Static files (if any needed, e.g. css)
	r.Static("/static", "./static")

	r.GET("/", func(c *gin.Context) {
		c.Redirect(http.StatusFound, "/leaderboard")
	})

	r.GET("/login", func(c *gin.Context) {
		c.HTML(http.StatusOK, "login.html", gin.H{})
	})

	r.POST("/login", func(c *gin.Context) {
		username := c.PostForm("username")
		password := c.PostForm("password")

		var id int
		var pwBcrypt string
		err := db.QueryRow("SELECT id, pw_bcrypt FROM users WHERE safe_name = ?", safeName(username)).Scan(&id, &pwBcrypt)
		if err != nil {
			c.HTML(http.StatusOK, "login.html", gin.H{"Error": "User not found"})
			return
		}

		// Verify password (using bcrypt)
		// bancho.py stores the bcrypt hash of the MD5 of the password (because the client sends MD5).
		// So we must MD5 the input password first.
		hasher := md5.New()
		hasher.Write([]byte(password))
		md5Password := hex.EncodeToString(hasher.Sum(nil))

		if err := bcrypt.CompareHashAndPassword([]byte(pwBcrypt), []byte(md5Password)); err != nil {
			// Fallback: try raw password just in case it was stored differently
			if err := bcrypt.CompareHashAndPassword([]byte(pwBcrypt), []byte(password)); err != nil {
				c.HTML(http.StatusOK, "login.html", gin.H{"Error": "Invalid password"})
				return
			}
		}

		// Set cookie
		c.SetCookie("user_id", strconv.Itoa(id), 3600*24, "/", "", false, true)
		c.Redirect(http.StatusFound, "/u/"+strconv.Itoa(id))
	})

	r.GET("/logout", func(c *gin.Context) {
		c.SetCookie("user_id", "", -1, "/", "", false, true)
		c.Redirect(http.StatusFound, "/")
	})

	r.GET("/leaderboard", func(c *gin.Context) {
		modeStr := c.DefaultQuery("mode", "0")
		mode, _ := strconv.Atoi(modeStr)
		
		// Get top 50 users by PP
		rows, err := db.Query(`
			SELECT u.id, u.name, u.country, s.pp, s.acc, s.plays 
			FROM stats s 
			JOIN users u ON s.id = u.id 
			WHERE s.mode = ? AND u.priv > 2 
			ORDER BY s.pp DESC LIMIT 50`, mode)
		if err != nil {
			c.String(http.StatusInternalServerError, "DB Error: %v", err)
			return
		}
		defer rows.Close()

		var users []map[string]interface{}
		rank := 1
		for rows.Next() {
			var uID, plays int
			var uName, uCountry string
			var pp float64
			var acc float64
			rows.Scan(&uID, &uName, &uCountry, &pp, &acc, &plays)
			users = append(users, map[string]interface{}{
				"Rank": rank,
				"ID": uID,
				"Name": uName,
				"Country": uCountry,
				"PP": int(pp), // round for display
				"Acc": fmt.Sprintf("%.2f%%", acc),
				"Plays": plays,
			})
			rank++
		}

		c.HTML(http.StatusOK, "leaderboard.html", gin.H{
			"Users": users,
			"Mode": mode,
			"LoggedIn": isLoggedIn(c),
		})
	})


	// Serve avatars
	r.GET("/avatar/:id", func(c *gin.Context) {
		id := c.Param("id")
		// simplistic sanitization to prevent directory traversal
		if _, err := strconv.Atoi(id); err != nil {
			c.String(http.StatusBadRequest, "Invalid ID")
			return
		}
		
		basePath := "../.data/avatars"
		extensions := []string{".jpg", ".jpeg", ".png"} // prioritize jpg
		
		var imgPath string
		for _, ext := range extensions {
			testPath := filepath.Join(basePath, id+ext)
			if _, err := os.Stat(testPath); err == nil {
				imgPath = testPath
				break
			}
		}

		if imgPath != "" {
			c.File(imgPath)
		} else {
			// Fallback to default avatar (online or local asset)
			// For now, redirect to a generic placeholder or serve a local default if available.
			// Let's use a reliable placeholder service or just 404 image.
			c.Redirect(http.StatusFound, "https://secure.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y") 
		}
	})

	// Handle avatar upload
	r.POST("/avatar", func(c *gin.Context) {
		userID := getCurrentUserID(c)
		if userID == 0 {
			c.Redirect(http.StatusFound, "/login")
			return
		}

		file, err := c.FormFile("avatar")
		if err != nil {
			c.String(http.StatusBadRequest, "Bad request")
			return
		}

		ext := strings.ToLower(filepath.Ext(file.Filename))
		if ext != ".jpg" && ext != ".jpeg" && ext != ".png" {
			c.String(http.StatusBadRequest, "Only jpg/png allowed")
			return
		}

		// Save file
		filename := strconv.Itoa(userID) + ext
		dst := filepath.Join("../.data/avatars", filename)
		
		// Remove old files with different extensions (optional, to avoid confusion)
		for _, e := range []string{".jpg", ".jpeg", ".png"} {
			if e != ext {
				os.Remove(filepath.Join("../.data/avatars", strconv.Itoa(userID)+e))
			}
		}

		if err := c.SaveUploadedFile(file, dst); err != nil {
			c.String(http.StatusInternalServerError, "Failed to save file: %v", err)
			return
		}

		c.Redirect(http.StatusFound, fmt.Sprintf("/u/%d", userID))
	})

	r.GET("/u/:id", func(c *gin.Context) {
		idStr := c.Param("id")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			c.String(http.StatusBadRequest, "Invalid ID")
			return
		}

		var user User
		err = db.QueryRow("SELECT id, name, country, creation_time, latest_activity FROM users WHERE id = ?", id).Scan(
			&user.ID, &user.Name, &user.Country, &user.CreationTime, &user.LatestActivity,
		)
		if err != nil {
			c.String(http.StatusNotFound, "User not found")
			return
		}

		modeStr := c.DefaultQuery("mode", "0")
		mode, _ := strconv.Atoi(modeStr)

		var stats Stats
		err = db.QueryRow("SELECT tscore, rscore, pp, plays, playtime, acc, max_combo FROM stats WHERE id = ? AND mode = ?", id, mode).Scan(
			&stats.TScore, &stats.RScore, &stats.PP, &stats.Plays, &stats.PlayTime, &stats.Acc, &stats.MaxCombo,
		)
		if err != nil {
			stats = Stats{}
		}
		stats.Mode = mode

		// Get Best Scores
		scoreRows, err := db.Query(`
			SELECT s.id, s.score, s.pp, s.acc, s.max_combo, s.mods, s.grade, s.play_time, s.map_md5,
			m.id, m.set_id, m.artist, m.title, m.version, m.creator, m.status
			FROM scores s
			JOIN maps m ON s.map_md5 = m.md5
			WHERE s.userid = ? AND s.mode = ? AND s.status = 2
			ORDER BY s.pp DESC LIMIT 10`, id, mode)
		
		var bestScores []Score
		if err == nil {
			defer scoreRows.Close()
			for scoreRows.Next() {
				var s Score
				var m Beatmap
				var playTimeStr string
				scoreRows.Scan(
					&s.ID, &s.Score, &s.PP, &s.Acc, &s.MaxCombo, &s.Mods, &s.Grade, &playTimeStr, &s.MapMD5,
					&m.ID, &m.SetID, &m.Artist, &m.Title, &m.Version, &m.Creator, &m.Status,
				)
				s.Beatmap = &m
				s.Date = playTimeStr
				bestScores = append(bestScores, s)
			}
		}

		c.HTML(http.StatusOK, "profile.html", gin.H{
			"User": user,
			"Stats": stats,
			"Scores": bestScores,
			"Mode": mode,
			"LoggedIn": isLoggedIn(c),
			"CurrentUserID": getCurrentUserID(c),
		})
	})

	r.POST("/change-password", func(c *gin.Context) {
		userID := getCurrentUserID(c)
		if userID == 0 {
			c.Redirect(http.StatusFound, "/login")
			return
		}

		oldPass := c.PostForm("old_password")
		newPass := c.PostForm("new_password")

		if len(newPass) < 8 {
			c.String(http.StatusBadRequest, "New password must be at least 8 characters")
			return
		}

		// Fetch current hash
		var currentHash string
		err := db.QueryRow("SELECT pw_bcrypt FROM users WHERE id = ?", userID).Scan(&currentHash)
		if err != nil {
			c.String(http.StatusInternalServerError, "DB Error")
			return
		}

		// Verify old password
		// Try md5 approach first
		hasher := md5.New()
		hasher.Write([]byte(oldPass))
		md5Old := hex.EncodeToString(hasher.Sum(nil))

		if err := bcrypt.CompareHashAndPassword([]byte(currentHash), []byte(md5Old)); err != nil {
			// Try raw
			if err := bcrypt.CompareHashAndPassword([]byte(currentHash), []byte(oldPass)); err != nil {
				c.String(http.StatusUnauthorized, "Old password incorrect")
				return
			}
		}

		// Hash new password
		hasherNew := md5.New()
		hasherNew.Write([]byte(newPass))
		md5New := hex.EncodeToString(hasherNew.Sum(nil))

		newBcrypt, err := bcrypt.GenerateFromPassword([]byte(md5New), bcrypt.DefaultCost)
		if err != nil {
			c.String(http.StatusInternalServerError, "Failed to hash password")
			return
		}

		_, err = db.Exec("UPDATE users SET pw_bcrypt = ? WHERE id = ?", string(newBcrypt), userID)
		if err != nil {
			c.String(http.StatusInternalServerError, "Failed to update password")
			return
		}

		c.Redirect(http.StatusFound, fmt.Sprintf("/u/%d", userID))
	})

	port := "8000" // Standard port matching nginx config
	log.Printf("Server starting on http://localhost:%s", port)
	r.Run(":" + port)
}

func isLoggedIn(c *gin.Context) bool {
	_, err := c.Cookie("user_id")
	return err == nil
}

func getCurrentUserID(c *gin.Context) int {
	cookie, err := c.Cookie("user_id")
	if err != nil {
		return 0
	}
	id, _ := strconv.Atoi(cookie)
	return id
}

func safeName(name string) string {
	return strings.ReplaceAll(strings.ToLower(name), " ", "_")
}
