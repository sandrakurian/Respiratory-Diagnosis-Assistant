from django.shortcuts import render
from .forms import SearchForm
from .models import Patients, RespiratoryData, Diagnosis
from django.http import JsonResponse
from .audio_utils import preprocess_audio, predict_from_features
import tensorflow as tf
from difflib import get_close_matches
import numpy as np

# Load the model on startup
model = tf.keras.models.load_model('gru_model.tf')

def home(request):
    return render(request, 'search/home.html')

def search(request):
    if request.method == 'POST':
        form = SearchForm(request.POST, request.FILES)
        if form.is_valid():
            input_type = form.cleaned_data['input_type']
            search_results = []
            if input_type == 'text':
                query = form.cleaned_data['query']
                matched_diagnoses = Diagnosis.objects.filter(diagnosis_name__icontains=query).select_related('patient_id')
                for diag in matched_diagnoses:
                    patient = diag.patient_id
                    for resp in patient.respiratory_data:
                        search_results.append({
                            'patient_number': patient.patient_id,
                            'age': patient.age,
                            'sex': patient.sex,
                            'disease': diag.diagnosis_name,
                            'audio_file': f"https://respiratory-diagnosis.s3.us-east-2.amazonaws.com/{resp['sound_file_path']}",
                            'annotation_file': f"https://respiratory-diagnosis.s3.us-east-2.amazonaws.com/{resp['annotation_file']}",
                            'recording_index': resp['recording_index'],
                            'chest_location': resp['chest_location'],
                            'acquisition_model': resp['acquisition_model'],
                            'recording_equipment': resp['recording_equipment'],
                            'respiratory_cycles': resp['respiratory_cycles'],
                            'similarity_score': None  # Not applicable here
                        })
                
                return render(request, 'search/result.html', {'search_results': search_results})

            elif input_type == 'audio':
                audio_file = request.FILES['audio_file']
                features = preprocess_audio(audio_file)
                prediction = predict_from_features(model, features)
                predicted_scores = np.squeeze(prediction)
                
                print(predicted_scores)
                predicted_indices = np.where(predicted_scores > 0.5)[0]
                predicted_diagnoses = Diagnosis.objects.filter(id__in=predicted_indices).select_related('patient_id')
                for diag in predicted_diagnoses:
                    patient = diag.patient_id
                    for resp in patient.respiratory_data:
                        search_results.append({
                            'patient_number': patient.patient_id,
                            'age': patient.age,
                            'sex': patient.sex,
                            'disease': diag.diagnosis_name,
                            'audio_file': f"https://respiratory-diagnosis.s3.us-east-2.amazonaws.com/{resp['sound_file_path']}",
                            'annotation_file': f"https://respiratory-diagnosis.s3.us-east-2.amazonaws.com/{resp['annotation_file']}",
                            'recording_index': resp['recording_index'],
                            'chest_location': resp['chest_location'],
                            'acquisition_model': resp['acquisition_model'],
                            'recording_equipment': resp['recording_equipment'],
                            'respiratory_cycles': resp['respiratory_cycles'],
                            'similarity_score': float(predicted_scores[diag.id])  # Assuming diag.id matches the index used in predictions
                        })
                
                return render(request, 'search/result.html', {'search_results': search_results})
                
        else:
            return render(request, 'search/search.html', {'form': form, 'message': 'Form is not valid. Please check your input.'})
    else:
        form = SearchForm()
        return render(request, 'search/search.html', {'form': form})
    
def about(request):
    return render(request, 'search/about.html')

def help(request):
    return render(request, 'search/help.html')

def contact(request):
    if request.method == 'POST':
        # Process feedback form submission
        feedback = request.POST.get('feedback')
        # Handle feedback submission (e.g., save to database)
        # For now, let's print the feedback to console
        print("Feedback:", feedback)
        return render(request, 'search/contact.html', {'message': 'Thank you for your feedback!'})
    else:
        return render(request, 'search/contact.html')
