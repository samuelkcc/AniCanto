"""The locale contract shared by initial writing and subsequent dialogue edits."""
REVISION='hong-kong-cantonese-2-spoken-register'
RULES='''廣東話台詞必須係香港廣東話（yue-HK），用繁體字及香港本地用字、慣用語同對話節奏。
寫得生動、有角色感：按人物性格同情緒選擇自然語氣、反應同句式；唔好句句同一種口吻。
 actor 讀得出感情：按情緒用自然語氣詞（呀、啦、喎、嘛、嘅、咋、吓、喂、哼）、問號同感嘆號；短促反應要短，長句要有停頓位置。
書面中文要改成口語：非常→好、什麼→乜嘢／咩、沒有→冇、不知道→唔知、不記得→唔記得、不會→唔會、不要→唔好、不能→唔可以、為什麼→點解、現在→而家、剛剛→啱啱、待會兒→陣間、這個／這裡→呢個／呢度、那個／那裡→嗰個／嗰度、我們／你們／他們→我哋／你哋／佢哋、進行→做、感覺→覺得、想要→想。
避免普通話直譯、書面中文套粵語字音、廣州地區慣用語同香港少用嘅地區用字。
唔好為咗本地化硬加潮語、粗口、口頭禪或香港地名；正式人物可以得體，兒童同長輩用字要合適。
保留原意、否定、關鍵數量、人名、人物關係同笑點；本地化唔可以作新劇情。
配音長度以原本日文發聲秒數為準：有 target_characters 就以該字數作目標，否則按 seconds 或 end-start 每秒約4.5個中文字估算。用精簡香港口語，刪冗餘主語、客套同無資訊重複，唔加字填時間。短反應要短。字數係目標，唔可以機械截字刪意思。生成後會量度錄音並調速，唔會推遲下一句。'''


def localize_messages(messages):
    result=[]
    for message in messages:
        row=dict(message);content=row.get('content')
        if row.get('role')=='system' and isinstance(content,str) and any(word in content.lower() for word in ('cantonese','廣東話','香港粵語','粤语','粵語')) and RULES not in content:
            row['content']=content+'\n需要生成或修改廣東話台詞時，遵守以下地區風格：\n'+RULES
        result.append(row)
    return result
