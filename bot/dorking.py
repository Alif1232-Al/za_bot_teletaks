DORK_CATEGORIES = {
    "admin": {
        "title": "Admin Panel",
        "description": "Find admin login pages",
        "dorks": [
            "site:* inurl:admin login",
            "site:* inurl:admin panel",
            "site:* intitle:\"admin login\"",
            "site:* inurl:administrator",
            "site:* inurl:wp-admin",
            "site:* inurl:cpanel",
            "site:* inurl:plesk",
            "site:* intitle:\"control panel\"",
        ],
    },
    "config": {
        "title": "Config & Database Files",
        "description": "Find exposed configuration files",
        "dorks": [
            "site:* ext:env \"DB_PASSWORD\"",
            "site:* ext:env \"DB_HOST\"",
            "site:* ext:xml inurl:config",
            "site:* ext:json inurl:config",
            "site:* ext:yml \"database\" \"password\"",
            "site:* ext:sql \"INSERT INTO\"",
            "site:* ext:sql \"VALUES\" password",
            "site:* ext:bak inurl:config",
        ],
    },
    "logs": {
        "title": "Log Files",
        "description": "Find exposed log files",
        "dorks": [
            "site:* ext:log \"password\"",
            "site:* ext:log \"error\" intext:exception",
            "site:* ext:log inurl:access.log",
            "site:* ext:log inurl:error.log",
            "site:* ext:log inurl:debug.log",
            "site:* inurl:log \"admin\" \"password\"",
        ],
    },
    "sensitive": {
        "title": "Sensitive Documents",
        "description": "Find exposed sensitive documents",
        "dorks": [
            "site:* ext:pdf \"confidential\"",
            "site:* ext:doc \"confidential\"",
            "site:* ext:xls \"password\"",
            "site:* ext:xlsx \"salary\"",
            "site:* ext:pdf \"password\" intext:email",
            "site:* inurl:backup \"passwords\"",
            "site:* inurl:backup \"credentials\"",
        ],
    },
    "cloud": {
        "title": "Cloud & AWS S3",
        "description": "Find exposed cloud storage",
        "dorks": [
            "site:s3.amazonaws.com \"ListBucketResult\"",
            "site:s3.amazonaws.com intitle:index.of",
            "site:s3.amazonaws.com \"<Key>\"",
            "site:storage.googleapis.com intitle:index.of",
            "site:blob.core.windows.net intitle:index.of",
            "site:digitaloceanspaces.com intitle:index.of",
        ],
    },
    "cameras": {
        "title": "IP Cameras & IoT",
        "description": "Find exposed cameras and IoT devices",
        "dorks": [
            "inurl:\"view/view.shtml\"",
            "intitle:\"Live View / - AXIS\"",
            "intitle:\"WVC\" \"WVC Admin Menu\"",
            "intitle:\"WVC\" \"WVC Configuration\"",
            "inurl:\"top.htm\" inurl:\"axis-cgi\"",
            "intitle:\"Network Camera\" \"live view\"",
            "intitle:\"IP Camera\" \"login\"",
        ],
    },
    "files": {
        "title": "Directory Listings",
        "description": "Find open directory listings",
        "dorks": [
            "intitle:\"index of /\" \"parent directory\"",
            "intitle:\"index of /\" \"backup\"",
            "intitle:\"index of /\" \"admin\"",
            "intitle:\"index of /\" \"config\"",
            "intitle:\"index of /\" \"password\"",
            "intitle:\"index of /\" \"private\"",
            "intitle:\"index of /\" \"upload\"",
        ],
    },
    "emails": {
        "title": "Email & Credentials",
        "description": "Find exposed emails and credentials",
        "dorks": [
            "site:* ext:txt \"@gmail.com\" password",
            "site:* ext:txt \"@yahoo.com\" password",
            "site:* intext:\"@\" intext:password ext:xls",
            "site:pastebin.com \"@\" \"password\"",
            "site:pastebin.com \"email\" \"password\"",
            "site:* ext:csv \"email\" \"password\"",
        ],
    },
    "php": {
        "title": "PHP Info & Vulns",
        "description": "Find PHP info pages and potential vulnerabilities",
        "dorks": [
            "ext:php intitle:phpinfo \"PHP Version\"",
            "inurl:phpinfo.php",
            "intitle:\"phpMyAdmin\" \"Welcome to phpMyAdmin\"",
            "inurl:phpmyadmin/index.php",
            "inurl:phpMyAdmin/server_databases.php",
            "intitle:\"PHP Error\" \"Fatal error\"",
        ],
    },
    "sql": {
        "title": "SQL Injection",
        "description": "Find potential SQL injection points",
        "dorks": [
            "inurl:\"id=\" inurl:\"&\"",
            "inurl:product.php?id=",
            "inurl:item.php?id=",
            "inurl:article.php?id=",
            "inurl:page.php?id=",
            "inurl:category.php?id=",
            "inurl:view.php?id=",
        ],
    },
    "subdomains": {
        "title": "Subdomain Enumeration",
        "description": "Find subdomains of a target",
        "dorks": [
            "site:*.target.com -www",
            "site:*.*.target.com",
            "inurl:target.com intitle:\"index of\"",
        ],
    },
}

DORK_HELP = """<b>Google Dorking Commands:</b>

/dork &lt;category&gt; - Show dorks in a category
/dork all - Show ALL dorks

<b>Available Categories:</b>
"""


def get_dork_list(category: str) -> list[str]:
    category = category.lower()
    if category == "all":
        result = []
        for cat in DORK_CATEGORIES.values():
            result.extend(cat["dorks"])
        return result
    cat = DORK_CATEGORIES.get(category)
    if cat:
        return cat["dorks"]
    return []


def get_category_info(category: str) -> dict | None:
    category = category.lower()
    return DORK_CATEGORIES.get(category)


def format_dork_list(category: str, dorks: list[str]) -> str:
    cat_info = get_category_info(category)
    title = cat_info["title"] if cat_info else category.title()
    desc = cat_info["description"] if cat_info else ""

    msg = f"<b>{title}</b>\n{desc}\n\n"
    for i, dork in enumerate(dorks, 1):
        query = dork.replace(" ", "+")
        url = f"https://www.google.com/search?q={query}"
        msg += f"{i}. <a href='{url}'>{dork}</a>\n"
    return msg


def format_categories_list() -> str:
    msg = DORK_HELP
    for key, cat in DORK_CATEGORIES.items():
        msg += f"  /dork_{key} - {cat['title']}\n"
    msg += "\n<b>Example:</b>\n/dork admin\n/dork all"
    return msg
