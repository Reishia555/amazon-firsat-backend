const puppeteer = require('puppeteer');

async function scrapeTrendyol() {
    const browser = await puppeteer.launch({
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    });

    const page = await browser.newPage();
    
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
    
    const products = [];
    
    try {
        const searchQueries = [
            'elektronik',
            'telefon',
            'bilgisayar',
            'ev-yasam',
            'moda'
        ];

        for (const query of searchQueries) {
            const url = `https://www.trendyol.com/sr?q=${query}&pi=1`;
            
            await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
            
            await page.waitForSelector('.p-card-wrppr', { timeout: 10000 });
            
            const pageProducts = await page.evaluate(() => {
                const productElements = document.querySelectorAll('.p-card-wrppr');
                const results = [];
                
                productElements.forEach((element, index) => {
                    if (index >= 20) return; // Limit to 20 products per query
                    
                    try {
                        const titleElement = element.querySelector('.prdct-desc-cntnr-name');
                        const priceElement = element.querySelector('.prc-box-dscntd');
                        const originalPriceElement = element.querySelector('.prc-box-orgnl');
                        const linkElement = element.querySelector('a');
                        const imageElement = element.querySelector('.p-card-img');
                        const discountElement = element.querySelector('.dsct-prcntg');
                        
                        if (!titleElement || !priceElement || !originalPriceElement || !linkElement) return;
                        
                        const title = titleElement.textContent.trim();
                        const currentPrice = parseFloat(priceElement.textContent.replace(/[^\d,]/g, '').replace(',', '.'));
                        const originalPrice = parseFloat(originalPriceElement.textContent.replace(/[^\d,]/g, '').replace(',', '.'));
                        const discountText = discountElement ? discountElement.textContent.trim() : '';
                        const discountPercent = discountText ? parseInt(discountText.replace('%', '')) : 0;
                        
                        if (discountPercent >= 40 && currentPrice > 0 && originalPrice > 0) {
                            results.push({
                                title: title,
                                current_price: currentPrice,
                                original_price: originalPrice,
                                discount_percent: discountPercent,
                                url: 'https://www.trendyol.com' + linkElement.getAttribute('href'),
                                image_url: imageElement ? imageElement.getAttribute('src') : '',
                                site: 'Trendyol'
                            });
                        }
                    } catch (error) {
                        console.error('Error processing product element:', error);
                    }
                });
                
                return results;
            });
            
            products.push(...pageProducts);
            
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
    } catch (error) {
        console.error('Scraping error:', error);
    } finally {
        await browser.close();
    }
    
    const uniqueProducts = products.filter((product, index, self) => 
        index === self.findIndex(p => p.url === product.url)
    );
    
    return uniqueProducts.slice(0, 50);
}

async function main() {
    try {
        const products = await scrapeTrendyol();
        console.log(JSON.stringify({
            success: true,
            products: products,
            count: products.length
        }));
    } catch (error) {
        console.log(JSON.stringify({
            success: false,
            error: error.message,
            products: [],
            count: 0
        }));
    }
}

if (require.main === module) {
    main();
}

module.exports = { scrapeTrendyol };