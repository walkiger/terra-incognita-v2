import os
import requests

# List of ArXiv IDs for the prioritized papers
paper_ids = [
    #"2603.17837", "2510.25741", "2604.17140", "2211.00568",
    #"2403.04571", "2209.02606", "2305.14970", "2410.01201"
    #"2111.09266","2106.04399","2301.12594","2210.03308",
    #"2302.06576","2502.17419","2311.11829","2505.21432",
    #"2410.03662","2506.10408","2501.04682","2502.07202",
    #"2407.06023","2507.02092","1510.02777","1602.05179",
    #"1211.5063","1312.6026","1502.02367","2202.01361",
    #"2303.02430","2408.05885","2511.09677","2503.06337",
    #"2111.09266","2106.04399","2301.12594","2210.03308",
    #"2302.06576","2502.17419","2311.11829","2505.21432",
    #"2410.03662","2506.10408","2501.04682","2502.07202",
    #"2407.06023","2507.02092","1510.02777","1602.05179",
    #"1211.5063","1312.6026","1502.02367","2202.01361",
    #"2303.02430","2408.05885","2511.09677","2503.06337",
    #"2412.20372","2501.02497","2602.02704","2309.05153",
    #"1901.08508","1606.03439","2412.16964","2505.01812",
    #"2601.02989","2503.01895"
]

def download_arxiv_pdfs(folder_path):

    for paper_id in paper_ids:
        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        file_path = os.path.join(folder_path, f"{paper_id}.pdf")
        
        print(f"Downloading {paper_id}...")
        try:
            response = requests.get(pdf_url, timeout=20)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Successfully saved to {file_path}")
            else:
                print(f"Failed to download {paper_id} (Status: {response.status_code})")
        except Exception as e:
            print(f"Error downloading {paper_id}: {e}")

if __name__ == "__main__":
    # Change 'Bengio_Cognitive_AI' to your desired path
    download_arxiv_pdfs(r"C:\Users\Michel Gaede\.cursor\projects\terra-incognita\research\incoming\new download")