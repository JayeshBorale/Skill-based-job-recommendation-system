from django.shortcuts import render,redirect
import PyPDF2
import docx
import joblib
import os
from django.conf import settings
from app1.naukri_scrapper import SeleniumNaukriScraper

from django.views import View 
from django.contrib import messages  


def load_models():

    try:
            
        models_dir = os.path.join(settings.BASE_DIR, 'job_suggestor', 'trained_models')
        
        model_path = os.path.join(models_dir, 'resume_classifier_model.pkl')
        vectorizer_path = os.path.join(models_dir, 'tfidf_vectorizer.pkl')
        encoder_path = os.path.join(models_dir, 'label_encoder.pkl')
        
        print(f"🔍 Loading models from: {models_dir}")
        
        
        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)
        encoder = joblib.load(encoder_path)

       

        
        print("✅ Models loaded successfully!")
        print(f"📊 Categories: {list(encoder.classes_)}")

       
        
        return model, vectorizer, encoder
        
    except Exception as e:
        print(f"❌ Error loading models: {e}")
        return None, None, None


model, vectorizer, encoder = load_models()

def extract_text_from_file(file):
    """Extract text from different file formats"""
    text = ""
    
    if file.name.endswith('.pdf'):
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    elif file.name.endswith(('.doc', '.docx')):
        try:
            doc = docx.Document(file)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            raise Exception(f"Error reading Word document: {str(e)}")
    
    elif file.name.endswith('.txt'):
        try:
            text = file.read().decode('utf-8')
        except Exception as e:
            raise Exception(f"Error reading text file: {str(e)}")
    
    else:
        raise Exception("Unsupported file format")
    
    return text.strip()

def predict_category(resume_text):
    """Make prediction using loaded models"""
    if model is None or vectorizer is None or encoder is None:
        raise Exception("ML models are not loaded properly")
    
    
    text_tfidf = vectorizer.transform([resume_text])
    
    
    prediction_encoded = model.predict(text_tfidf)[0]
    prediction_label = encoder.inverse_transform([prediction_encoded])[0]
    
    
    probabilities = model.predict_proba(text_tfidf)[0]
    confidence = max(probabilities)
    
    
    all_categories = encoder.classes_
    category_probabilities = {
        category: round(prob * 100, 2) 
        for category, prob in zip(all_categories, probabilities)
    }
    
    return {
        'category': prediction_label,
        'confidence': round(confidence * 100, 2),
        'all_probabilities': category_probabilities
    }

def home(request):
    resume_text = ""
    prediction_result = None
    error = None
    
    if request.method == "POST" and request.FILES.get('resume_file'):
        try:
            
            uploaded_file = request.FILES['resume_file']
            
            
            resume_text = extract_text_from_file(uploaded_file)
            
            
            
            
            if resume_text.strip():
                prediction_result = predict_category(resume_text)
                print(f"🎯 PREDICTION: {prediction_result['category']}")
                print(f"📊 CONFIDENCE: {prediction_result['confidence']}%")
                request.session['prediction_result'] = prediction_result['category']
                return redirect('test_scraper')
            
        except Exception as e:
            error = f'Error processing file: {str(e)}'
            print(f"❌ ERROR: {error}")

    return render(request, 'home.html', {
        'resume_text': resume_text,
        'prediction': prediction_result,
        'error': error,
        
    })

def result_views(request):
    prediction_result = request.session.get('prediction_result')
    resume_text_preview = request.session.get('resume_text_preview')
    if not prediction_result:
        
        return redirect('home')

    return render(request,'result.html',{'prediction_result':prediction_result})



class JobRecommendationsView(View):
    """
    Show job recommendations from Naukri.com using Selenium
    """
    def get(self, request):
        prediction_result = request.session.get('prediction_result')
        
        print(f"\n🎯 Starting Selenium-based job search for: {prediction_result}")
        
        if not prediction_result:
            messages.warning(request, 'Please upload a resume first to get job recommendations')
            return redirect('home')
        
        
        skill_mapping = {
            'Data Science': 'data science',
            'HR': 'human resources',
            'Design': 'graphic design',
            'Information Technology': 'software development',
            'Teacher': 'teaching',
            'Advocate': 'lawyer',
            'Business Development': 'business development',
            'Healthcare': 'healthcare',
            'Fitness': 'fitness trainer',
            'Agriculture': 'agriculture',
            'BPO': 'customer service',
            'Sales': 'sales',
            'Mechanical Engineer': 'mechanical engineering',
            'Java Developer': 'java developer',
            'Automobile': 'automobile engineering',
            'Digital Marketing': 'digital marketing',
            'Civil Engineer': 'civil engineering',
            'Operations Manager': 'operations management',
            'Electrical Engineering': 'electrical engineering',
            'Network Security Engineer': 'network security',
            'Python Developer': 'python developer',
            'ERP': 'ERP consultant',
            'DotNet Developer': '.net developer',
            'Web Designing': 'web designer',
        }
        
        search_skill = skill_mapping.get(prediction_result, prediction_result.lower())
        
        
        location = request.GET.get('location', 'bangalore')
        experience = request.GET.get('experience', '0')
        
        print(f"🔍 Search parameters:")
        print(f"  Skill: {search_skill}")
        print(f"  Location: {location}")
        print(f"  Experience: {experience}")
        
        
        scraper = None
        jobs = []
        
        try:
            
            scraper = SeleniumNaukriScraper(headless=True)
            
            
            jobs = scraper.search_jobs(
                skill=search_skill,
                location=location,
                experience=experience,
                max_results=15
            )
            
            print(f"\n✅ Selenium search completed: {len(jobs)} jobs found")
            
        except Exception as e:
            print(f"❌ Selenium error: {e}")
            import traceback
            traceback.print_exc()
            
             
            if not jobs:
                print("🔄 Providing fallback sample jobs...")
                jobs = self._get_sample_jobs(search_skill, location)
        
        finally:
        
            if scraper:
                try:
                    scraper.close()
                except:
                    pass
        
        
        jobs = self._match_jobs_with_skill(jobs, search_skill)
        
        
        if jobs:
            print(f"\n📋 FINAL JOBS TO DISPLAY ({len(jobs)}):")
            for i, job in enumerate(jobs[:5], 1):
                print(f"{i}. {job.get('title', 'No Title')}")
                print(f"   Company: {job.get('company', 'N/A')}")
                print(f"   Score: {job.get('relevance_score', 0)}")
        
        context = {
            'prediction_result': prediction_result,
            'search_skill': search_skill,
            'jobs': jobs,
            'location': location,
            'total_jobs': len(jobs),
            'confidence': request.session.get('confidence', 0)
        }
        
        return render(request, 'jobs/job_recommendations.html', context)
    
    def _match_jobs_with_skill(self, jobs, skill):
        """Calculate relevance score for each job"""
        if not jobs:
            return []
        
        for job in jobs:
            title = job.get('title', '').lower()
            desc = job.get('description', '').lower()
            skills = [s.lower() for s in job.get('skills', [])]
            
            skill_lower = skill.lower()
            
            score = 0
            if skill_lower in title:
                score += 3
            if any(skill_lower in s for s in skills):
                score += 2
            if skill_lower in desc:
                score += 1
            
            job['relevance_score'] = score
        
        return sorted(jobs, key=lambda x: x['relevance_score'], reverse=True)
    
    def _get_sample_jobs(self, skill, location):
        """Get sample jobs for demonstration"""
        return [
            {
                'title': f'{skill.title()} Developer',
                'company': 'Tech Solutions Inc.',
                'location': location.title() if location else 'Bangalore',
                'experience': '2-5 years',
                'salary': '₹6,00,000 - ₹10,00,000 PA',
                'description': f'Looking for {skill} developer with relevant experience.',
                'skills': [skill, 'Python', 'Django', 'REST API'],
                'posted_date': 'Recently',
                'url': 'https://www.naukri.com/job-listing',
                'source': 'Naukri.com',
                'relevance_score': 3
            },
            {
                'title': f'Senior {skill.title()} Engineer',
                'company': 'Software Corp',
                'location': location.title() if location else 'Bangalore',
                'experience': '5-8 years',
                'salary': '₹10,00,000 - ₹15,00,000 PA',
                'description': f'Senior position for {skill} professional.',
                'skills': [skill, 'Java', 'Spring Boot'],
                'posted_date': '1 week ago',
                'url': 'https://www.naukri.com/job-listing',
                'source': 'Naukri.com',
                'relevance_score': 2
            }
        ]

def test_selenium_view(request):
    """Test Selenium scraper directly"""
    skill =  request.session.get('prediction_result')
    location = request.GET.get('location', 'bangalore')
    
    print(f"\n🧪 TESTING SELENIUM SCRAPER")
    print(f"Skill: {skill}")
    print(f"Location: {location}")
    
    scraper = SeleniumNaukriScraper(headless=True)  
    
    try:
        jobs = scraper.search_jobs(skill, location, max_results=10)
        
        print(f"\n✅ Found {len(jobs)} jobs")
        
        
        for i, job in enumerate(jobs, 1):
            print(f"\n{i}. {job.get('title', 'No Title')}")
            print(f"   Company: {job.get('company', 'N/A')}")
            print(f"   Location: {job.get('location', 'N/A')}")
            print(f"   URL: {job.get('url', 'N/A')}")
        
        return render(request, 'test_scrapper.html', {
            'jobs': jobs,
            'skill': skill,
            'location': location,
            'total': len(jobs)
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return render(request, 'test_selenium.html', {
            'error': str(e),
            'skill': skill,
            'location': location,
            'jobs': []
        })
    
    finally:
        if 'scraper' in locals():
            scraper.close()