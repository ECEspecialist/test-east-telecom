from .models import Department

def department_list(request):
    return {
        'departments': Department.objects.all()
    }
