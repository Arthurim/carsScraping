import bs4
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from difflib import SequenceMatcher
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import datetime

chrome_options = Options()
chrome_options.add_argument("--window-size = 1920,1080")
chromeDriver_path = "C:/dev/chromedrivers/chromedriver.exe"

baseUrl_uk="https://www.autotrader.co.uk/car-search?sort=relevance&radius=1500&postcode=e148hl&onesearchad=Used&onesearchad=Nearly%20New&onesearchad=New&keywords=left%20hand%20drive%20lhd&page="

miles_to_km = 1.60934
epsilon_km = 50000
epsilon_years = 2
maxPrice_uk = 30000.0
minDiffPrice = 3000
Nb_pages = 3 #10
max_km = 150000
path = "C:/dev/carScraping/data/"

autotrader = pd.DataFrame(columns = ["title_uk", "brand_uk", "model_uk", "price_uk (gbp)", "year_uk", "kilometrage_uk", "fuelType_uk", "bodyType_uk", "gearBox_uk", "link_uk", "keep_uk"])
leparking = pd.DataFrame(columns = ["brand_fr", "model_fr", "price_fr (eur)", "year_fr", "kilometrage_fr", "fuelType_fr", "gearBox_fr", "link_fr"])
final_result = pd.DataFrame(columns = ["title_uk", "brand_uk", "model_uk", "price_uk (gbp)", "year_uk", "kilometrage_uk", "fuelType_uk", "bodyType_uk", "gearBox_uk", "link_uk", "brand_fr", "model_fr", "price_fr (eur)", "year_fr", "kilometrage_fr", "fuelType_fr", "gearBox_fr", "link_fr"])

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def log_this(s,f):
    save_string_to_text_file(s,f)
    print(s)

def save_string_to_text_file(s,f):
    text_file = open(f, "a")
    text_file.write(s)
    text_file.close()

def getSubject():
    now = datetime.datetime.now()
    mth = now.strftime("%b")
    d = str(now.day)
    options = {'0' : 'th',
               '1' : 'st',
               '2' : 'th',
               '3' : 'rd',
               '4' : 'th',
               '5' : 'th',
               '6' : 'th',
               '7' : 'th',
               '8' : 'th',
               '9' : 'th'}
    c = options[str(d)[-1]]
    subject = "Left hand drive cars in the UK - " + d+c+" "+mth + " " + str(now.year)
    return subject

def getMessage(emailfrom,emailto,fileToSend,epsilon_km,epsilon_years,maxPrice_uk,minDiffPrice):
    msg = MIMEMultipart("alternative", None, [MIMEText("Voitures avec volant a gauche a vendre en UK cette semaine.\n" +\
                                                      "Criteres de recherche: \n \
                                                          - meme kilometrage a "+str(epsilon_km)+" km pres \n \
                                                          - meme annee a "+str(epsilon_years)+" ans pres \n \
                                                          - prix maximal en gbp: "+str(maxPrice_uk)+" \n \
                                                          - difference de prix (euros) mediane minimum: "+str(minDiffPrice))])
    msg["From"] = emailfrom
    msg["To"] = ", ".join(emailto)
    msg["Subject"] = getSubject()
    msg.preamble = "Please find attached the left hand drive cars for sale in the UK this week \n Arthur Bagourd"
    msg["Body"] = "rr"
    ctype, encoding = mimetypes.guess_type(fileToSend)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"

    maintype, subtype = ctype.split("/", 1)

    if maintype == "text":
        fp = open(fileToSend)
        # Note: we should handle calculating the charset
        attachment = MIMEText(fp.read(), _subtype = subtype)
        fp.close()
    elif maintype == "image":
        fp = open(fileToSend, "rb")
        attachment = MIMEImage(fp.read(), _subtype = subtype)
        fp.close()
    elif maintype == "audio":
        fp = open(fileToSend, "rb")
        attachment = MIMEAudio(fp.read(), _subtype = subtype)
        fp.close()
    else:
        fp = open(fileToSend, "rb")
        attachment = MIMEBase(maintype, subtype)
        attachment.set_payload(fp.read())
        fp.close()
        encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename = fileToSend)
    msg.attach(attachment)
    return msg

def sendMessage(msg,emailfrom,emailto,username,password):
    server = smtplib.SMTP("smtp.gmail.com:587")
    server.starttls()
    server.login(username,password)
    server.sendmail(emailfrom, emailto, msg.as_string())
    server.quit()
   
logs = ""
k = 0
counter_car_added = 0
keywords = ["lhd", "left hand drive", "left-hand drive", "left-hand-drive"]

msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - INFO - " + "Autotrader: starting\n"
log_this(msg, path + "logs.txt")
#%%
# loop over N first pages
for page_number_j in range(1, Nb_pages):
    msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - INFO - " + "page "+str(page_number_j)+"\n"
    log_this(msg, path+"logs.txt")
    url = baseUrl_uk + str(page_number_j)
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, 'html.parser')
    li_box = soup.find_all("li", {"class":"search-page__result"})
    # loop over each annonce and get the base info
    for i in range(len(li_box)):
        try:
            price = float(li_box[i].find_all("div",{'class':'vehicle-price'})[0].get_text().replace("£","").replace(",",""))
            title = li_box[i].find_all("h2",{'class':'listing-title title-wrap'})[0].get_text().replace("\n","")
            brand = title.split(" ")[0].lower()
            model = title.split(" ")[1] + " " + title.split(" ")[2]
            listingInformations = li_box[i].find_all("ul",{'class':"listing-key-specs "})[0].get_text().split("\n")
            for information in listingInformations:
                if "miles" in information:
                    mileage = float(information.split(" ")[0].replace(",",""))
            year = int(listingInformations[1][0:4])
            kilometrage = mileage * miles_to_km
            bodyType = listingInformations[2]
            fuelType = listingInformations[len(listingInformations)-2]
            gearBox = listingInformations[len(listingInformations)-3]
            link = "https://www.autotrader.co.uk/classified/advert/"+li_box[i].find_all("a",{"class":"js-click-handler listing-fpa-link tracking-standard-link"})[0]["href"].split("/")[3].split("?")[0]
            if kilometrage< max_km:
                autotrader.loc[counter_car_added] = [title,brand,model,price,year,kilometrage,fuelType,bodyType,gearBox,link,False]
                counter_car_added+= 1
        except:
            msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - INFO - " + "autotrader error for annonce " +str(i)+" on page "+str(page_number_j)+"\n"
            log_this(msg, path+"logs.txt")
   
    links = autotrader["link_uk"].tolist()
    
    # for each of the link gathered look at description to check it is a lhd car
    for i in range(len(links)):
        try:
            link = links[i]
            keep = False
            driver = webdriver.Chrome(chromeDriver_path,options = chrome_options)
            driver.get(link)
            html = driver.page_source
            soup = bs4.BeautifulSoup(html, 'lxml')
            #description = soup.find_all("p", {"class":"truncated-text fpa__description atc-type-picanto"})[0].get_text().lower()
            description = soup.find_all("section", {"class":"description-intro"})[0].get_text().lower()
            # description-intro__excerpt atc-type-picanto
            title = soup.find_all("div",{"class":"advert-heading fpa__price-confidence-advert-heading"})[0].get_text().lower()
            for word in keywords:
                if word in title or word in description:
                    keep = True
            autotrader.at[k,"keep_uk"] = keep
            k = k+1
            time.sleep(10)
            driver.close()
        except:
            msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - ERROR - " + "Looking at the description did not work for annonce " +str(i)+" on page "+str(page_number_j)+"\n"
            log_this(msg, path+"logs.txt")
    
    
now = datetime.datetime.now()
autotrader[autotrader["keep_uk"] == True].to_csv(path + 'scrapedCarInfo_' + now.strftime('%Y_%m_%d') + '.csv', sep = ";")
autotraderToInvestigate = autotrader[autotrader["keep_uk"] == True]
autotraderToInvestigate = autotraderToInvestigate.dropna()
nb_car_retained = len(autotraderToInvestigate)
msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - INFO - " + "Finished looking for lhd cars in the UK on Autotrader. \
      \n    nb of pages seen: " + str(Nb_pages) + "\
      \n    nb of cars retained: " + str(nb_car_retained) + "\n"
log_this(msg, path + "logs.txt")

#%%
if(nb_car_retained>0):

    msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - INFO - " + "\nFinding equivalent cars in France on leparking: starting\n"
    log_this(msg, path + "logs.txt")

    n = 0
    # now for each lhd car in the UK go find cars in Fr that look the same
    for j in range(3): #len(autotraderToInvestigate)):
        row = autotraderToInvestigate.iloc[j]
        keywords = row["brand_uk"] + " " + row["model_uk"]
        keywords = keywords.replace("left","").replace("hand","").replace("drive","")
        url = "http://www.leparking.fr/#!/voiture-occasion/"+keywords.replace(" ", "-") + \
            ".html%3Fid_pays%3D18%26slider_km%3D"+str(int(row["kilometrage_uk"]-epsilon_km))+ \
            "%7C"+str(int(row["kilometrage_uk"]+epsilon_km))+ \
            "%26slider_millesime%3D"+str(row['year_uk']-epsilon_years)+"%7C"+str(row['year_uk']+epsilon_years)
        driver = webdriver.Chrome(chromeDriver_path,chrome_options = chrome_options)
        driver.get(url)
        html = driver.page_source
        soup = bs4.BeautifulSoup(html, 'lxml')
        k = 0
        li_box = soup.find_all("section", {"class":"clearfix"})
        # for eacch post on the page
        for i in range(len(li_box)):
            try:
                title = li_box[i].find_all("div",{"class":"block-title-list"})[0]
                link="http://www.leparking.fr/"+li_box[i].find_all("a",{"class":"external btn-plus no-partenaire-btn"})[0]['href']
                brand=title.find("span",{"class":"title-block brand"}).get_text()
                model = title.find("span",{"class":"sub-title title-block"}).get_text()
                price = li_box[i].find_all("p",{"class":"prix"})[0].get_text().split(' ')
                p = ''
                for e in price:
                    if e!= ' ':
                        p+= e
                price = float(p.replace('\n', '').replace('€',''))
                bandeau = li_box[i].find_all("ul",{"class":"info clearfix"})[0].get_text().split("\n")
                l = []
                for e in bandeau:
                    if e != '':
                        l.append(e)
                year = l[2]
                kilometrage = l[1].split(" ")[:-1]
                kilometrage = int(kilometrage[0]+kilometrage[1])
                fuelType = l[0]
                gearBox = l[3]
                leparking.loc[k] = [brand,model,price,year,kilometrage,fuelType,gearBox,link]
                k+= 1
            except Exception as ex:
                msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - ERROR - " + "le parking error "+str(j)+str(i) + "\n" +str(ex) +"\n"
                log_this(msg, path+"logs.txt")
        driver.close()
       
        for r in range(len(leparking)):
            c = pd.concat([row[:10], leparking.iloc[r]], axis = 0).reset_index()
            c.columns = [0,1]
            final_result.loc[n] = c[1].tolist()
            n+= 1
    final_result['price_uk (eur)'] = final_result['price_uk (gbp)']*1.16        
    lisOfIndexToDrop = []        
    for r in range(len(final_result)):
        row = final_result.iloc[r]        
        if (not similar(row["brand_fr"],row["brand_uk"])>0.5) or (not similar(row["model_fr"],row["model_uk"])>0.2):
            lisOfIndexToDrop.append(r)
    
    final_result = final_result.drop(final_result.index[[lisOfIndexToDrop]])   
    lisOfIndexToDrop = []
    for title_uk in final_result.title_uk.unique():
        mean_price_fr = final_result[final_result["title_uk"] == title_uk]["price_fr (eur)"].median()
        if(abs(mean_price_fr-final_result[final_result["title_uk"] == title_uk]["price_uk (eur)"].mean()))<minDiffPrice:
            lisOfIndexToDrop + final_result[final_result["title_uk"] == title_uk].index.tolist()
#%%
    final_result = final_result.drop(final_result.index[[lisOfIndexToDrop]])
    final_result = final_result.drop_duplicates()
    final_result = final_result[final_result['price_uk (gbp)'] < = maxPrice_uk]
    final_result.to_csv(path + 'final_comparison_' + now.strftime('%Y_%m_%d') + '.csv', sep = ";")
    final_result.to_excel(path + 'final_comparison_' + now.strftime('%Y_%m_%d') + '.xlsx')
    msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - INFO - " + "leparking: finished" + "\n"
    log_this(msg, path + "logs.txt")
    
    msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - INFO - " + "Sending email" + "\n"
    log_this(msg, path + "logs.txt")
    
    emailfrom = "arthurautomaticemail@gmail.com"
    emailto = ["arthurbagourd56@gmail.com"]#, "aika.baitas@gmail.com", "leturmy56@gmail.com"]
    fileToSend = path + "final_comparison.xlsx"
    username = emailfrom
    password = "arthurautomatic1011*"
    
    msgToSend = getMessage(emailfrom, emailto, fileToSend, epsilon_km, epsilon_years, maxPrice_uk, minDiffPrice)
    sendMessage(msgToSend, emailfrom, emailto, username, password)
    
    msg = datetime.datetime.today().strftime("%Y.%m.%d %H:%M:%S.%f") + " - INFO - " + "Emails sent. Scraper finished." + "\n"
    log_this(msg, path + "logs.txt")

#%%