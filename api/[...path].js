// api/[...path].js
// PROXY KHUSUS UNTUK https://www.ivasms.com/
// Domain output: ivasmsbyzuue.wilzu.web.id (atau subdomain apapun)

const TARGET = 'https://www.ivasms.com';

export default async function handler(req, res) {
  // Ambil path dari URL
  const { path } = req.query;
  let targetPath = '';
  if (path) {
    targetPath = Array.isArray(path) ? path.join('/') : path;
  }

  // Ambil query string (parameter setelah ?)
  const queryString = req.url?.includes('?') ? req.url.split('?')[1] : '';

  // Bangun URL tujuan
  const targetUrl = `${TARGET}/${targetPath}${queryString ? '?' + queryString : ''}`;

  try {
    // Siapkan body untuk POST/PUT/DELETE
    let body = undefined;
    if (!['GET', 'HEAD'].includes(req.method)) {
      const chunks = [];
      for await (const chunk of req) {
        chunks.push(chunk);
      }
      body = Buffer.concat(chunks);
    }

    // Kirim request ke ivasms.com
    const response = await fetch(targetUrl, {
      method: req.method,
      headers: {
        'User-Agent': req.headers['user-agent'] || 'Vercel-Proxy',
        'Accept': req.headers['accept'] || '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        ...(req.headers['authorization'] && { 'Authorization': req.headers['authorization'] }),
        ...(req.headers['cookie'] && { 'Cookie': req.headers['cookie'] }),
        ...(req.headers['content-type'] && { 'Content-Type': req.headers['content-type'] }),
      },
      body: body,
    });

    // Baca response
    const responseData = await response.arrayBuffer();

    // Kirim balik ke client
    res.status(response.status);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', '*');

    const contentType = response.headers.get('content-type');
    if (contentType) res.setHeader('Content-Type', contentType);

    const setCookie = response.headers.get('set-cookie');
    if (setCookie) res.setHeader('Set-Cookie', setCookie);

    res.send(Buffer.from(responseData));

  } catch (error) {
    res.status(500).json({
      error: 'Proxy Gagal',
      message: error.message,
      target: targetUrl
    });
  }
}

// Matikan bodyParser biar bisa baca raw body
export const config = {
  api: {
    bodyParser: false,
  },
};
