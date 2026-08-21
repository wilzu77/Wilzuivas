
const express = require('express');
const session = require('express-session');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = 3000;

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(cors({ origin: 'http://localhost:3000', credentials: true }));

app.use(session({
    secret: 'rahasia-gopay-sederhana',
    resave: false,
    saveUninitialized: false,
    cookie: { maxAge: 1000 * 60 * 60 * 24 }
}));

// Pastikan folder public ada
const publicDir = path.join(__dirname, 'public');
if (!fs.existsSync(publicDir)) {
    console.error('❌ Folder "public" tidak ditemukan! Buat folder "public" dan letakkan file HTML di dalamnya.');
    process.exit(1);
}

// Sajikan file statis dari folder public
app.use(express.static(publicDir));

// File users
const USERS_FILE = path.join(__dirname, 'users.json');
function readUsers() {
    if (!fs.existsSync(USERS_FILE)) return [];
    return JSON.parse(fs.readFileSync(USERS_FILE, 'utf8'));
}
function writeUsers(users) {
    fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}

function ensureAdmin() {
    const users = readUsers();
    if (!users.some(u => u.email === 'wilzu@gmail.com')) {
        users.push({ email: 'wilzu@gmail.com', password: 'wilzu222333' });
        writeUsers(users);
        console.log('✅ Admin: wilzu@gmail.com / wilzu222333');
    }
}
ensureAdmin();

// ===== API =====
app.get('/api/session', (req, res) => {
    if (req.session.user) {
        res.json({ loggedIn: true, user: req.session.user });
    } else {
        res.json({ loggedIn: false });
    }
});

app.post('/api/login', (req, res) => {
    const { email, password } = req.body;
    const users = readUsers();
    const user = users.find(u => u.email === email && u.password === password);
    if (user) {
        req.session.user = { email: user.email };
        res.json({ success: true, user: req.session.user });
    } else {
        res.status(401).json({ success: false, message: 'Email atau password salah.' });
    }
});

app.post('/api/register', (req, res) => {
    const { email, password } = req.body;
    const users = readUsers();
    if (!email || !password) return res.status(400).json({ success: false, message: 'Semua kolom wajib diisi.' });
    if (password.length < 4) return res.status(400).json({ success: false, message: 'Password minimal 4 karakter.' });
    if (users.find(u => u.email === email)) return res.status(400).json({ success: false, message: 'Email sudah terdaftar.' });
    users.push({ email, password });
    writeUsers(users);
    req.session.user = { email };
    res.json({ success: true, user: req.session.user });
});

app.post('/api/logout', (req, res) => {
    req.session.destroy();
    res.json({ success: true });
});

app.post('/api/pay', (req, res) => {
    if (!req.session.user) return res.status(401).json({ success: false, message: 'Harus login.' });
    const { amount, name, email } = req.body;
    const nominal = parseInt(amount) || 0;
    const fee = 300;
    const total = nominal + fee;
    const transaction = {
        name,
        email,
        amount: nominal,
        total,
        fee,
        date: new Date().toLocaleString('id-ID')
    };
    res.json({ success: true, transaction });
});

// ===== WD =====
const WD_FILE = path.join(__dirname, 'withdraws.json');
function readWithdraws() {
    if (!fs.existsSync(WD_FILE)) return [];
    return JSON.parse(fs.readFileSync(WD_FILE, 'utf8'));
}
function writeWithdraws(wds) {
    fs.writeFileSync(WD_FILE, JSON.stringify(wds, null, 2));
}

app.post('/api/withdraw/request', (req, res) => {
    if (!req.session.user) return res.status(401).json({ success: false, message: 'Harus login.' });
    const { amount, bank, account } = req.body;
    const nominal = parseInt(amount);
    if (!nominal || nominal < 20000) {
        return res.status(400).json({ success: false, message: 'Minimal WD Rp 20.000' });
    }
    const wds = readWithdraws();
    const newWd = {
        id: Date.now().toString(),
        email: req.session.user.email,
        amount: nominal,
        bank,
        account,
        status: 'pending',
        date: new Date().toLocaleString('id-ID')
    };
    wds.push(newWd);
    writeWithdraws(wds);
    res.json({ success: true, withdraw: newWd });
});

app.get('/api/withdraw/list', (req, res) => {
    if (!req.session.user) return res.status(401).json({ success: false, message: 'Unauthorized' });
    if (req.session.user.email !== 'wilzu@gmail.com') {
        return res.status(403).json({ success: false, message: 'Hanya admin' });
    }
    res.json({ success: true, withdraws: readWithdraws() });
});

app.post('/api/withdraw/update', (req, res) => {
    if (!req.session.user) return res.status(401).json({ success: false, message: 'Unauthorized' });
    if (req.session.user.email !== 'wilzu@gmail.com') {
        return res.status(403).json({ success: false, message: 'Hanya admin' });
    }
    const { id, status } = req.body;
    const wds = readWithdraws();
    const idx = wds.findIndex(w => w.id === id);
    if (idx === -1) return res.status(404).json({ success: false, message: 'Request tidak ditemukan' });
    wds[idx].status = status;
    writeWithdraws(wds);
    res.json({ success: true, withdraw: wds[idx] });
});

// ===== ROUTE UTAMA dengan pengecekan file =====
app.get('/', (req, res) => {
    if (req.session.user) {
        const filePath = path.join(publicDir, 'index.html');
        // Cek apakah file ada
        if (!fs.existsSync(filePath)) {
            console.error('❌ File index.html tidak ditemukan di:', filePath);
            return res.status(404).send('File index.html tidak ditemukan. Pastikan ada di folder public.');
        }
        res.sendFile(filePath);
    } else {
        const filePath = path.join(publicDir, 'login.html');
        if (!fs.existsSync(filePath)) {
            console.error('❌ File login.html tidak ditemukan di:', filePath);
            return res.status(404).send('File login.html tidak ditemukan.');
        }
        res.sendFile(filePath);
    }
});

// Fallback untuk file statis yang tidak ketemu (opsional)
app.use((req, res) => {
    res.status(404).send('Halaman tidak ditemukan.');
});

app.listen(PORT, () => {
    console.log(`🚀 Server berjalan di http://localhost:${PORT}`);
    console.log(`📁 Folder public: ${publicDir}`);
    console.log('🔑 Admin: wilzu@gmail.com / wilzu222333');
});
