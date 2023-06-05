from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled

def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_answers.append(choice_id)
    return submitted_answers

def show_exam_result(request, course_id, submission_id):
    # Get course and submission based on their ids
    course = get_object_or_404(Course, pk=course_id)
    submission=Submission.objects.get(id=submission_id)
    # Get the selected choice ids from the submission record
    selected_choices = submission.choices
    total_score = 0
    total_question_weight = 0
    question_array = []
    question_count = Question.objects.filter(course_id=course_id).count()
    questions = Question.objects.filter(course_id=course_id)

    for choice in selected_choices.all():
        if choice.choice_correct:
            total_score += Question.objects.get(id=choice.question.id).grade_point
        if Question.objects.get(id=choice.question.id) not in question_array:
            question_array.append(Question.objects.get(id=choice.question.id))
            total_question_weight += Question.objects.get(id=choice.question.id).grade_point
    #logic for the case where no checkbox is selected for a problem
    unanswered_questions = list(set(questions)-set(question_array))
    #now find the weights of these questions
    for question in unanswered_questions:
        total_question_weight += question.grade_point

    # For each selected choice, check if it is a correct answer or not
    # Calculate the total score
    context = {
        'score':total_score,
        'course': course,
        'selected_ids':selected_choices,
        'grade':(total_score*100)/total_question_weight,
        'submission':submission,
        'questions':questions,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)

#Create a submit view def submit(request, course_id):
def submit(request, course_id):
    """
     to create an exam submission record for a course enrollment,
    you may implement it based on following logic:

    Get the current user and the course object, 
    then get the associated the enrollment object
    (HINT: Enrollment.objects.get(user=..., course=...))
    """ 
    #print(dir(request.user._wrapped))
    usr = request.user.username
    user_obj = User.objects.get(username=usr)
    user_id = user_obj.id
    enroll = Enrollment.objects.get(user=user_id, course=course_id)
    """
    Create a new submission object referring to the enrollment
    (HINT: Submission.objects.create(enrollment=...))
    """ 
    submission=Submission.objects.create(enrollment=enroll)
    """
    Collect the selected choices from HTTP request object 
    (HINT: you could use request.POST to get the payload 
    dictionary, and
    get the choice id from the dictionary values, 
    """ 
    selected_choices = extract_answers(request)
    """ ...
    an example code snippet is also provided)
    Add each selected choice object to the submission object
    """ 
    #previously submission += selected_choices
    submission.choices.set(selected_choices)
    submission.save()
    """
    Redirect to a show_exam_result view with the submission id 
    to show the exam result
    Configure urls.py to route the new submit view 
    such as path('<int:course_id>/submit/', ...),
    """
    new_url = "/onlinecourse/course/"+str(course_id)+"/submission/"+str(submission.id)+"/result/"
    return redirect(new_url)

# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        context['questions'] = Question.objects.filter(course=course)
        context['choices'] = Choice.objects.filter(question__in = context['questions'])
        return context


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
#def submit(request, course_id):


# <HINT> A example method to collect the selected choices from the exam form from the request object
#def extract_answers(request):
#    submitted_anwsers = []
#    for key in request.POST:
#        if key.startswith('choice'):
#            value = request.POST[key]
#            choice_id = int(value)
#            submitted_anwsers.append(choice_id)
#    return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score


