import json
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse,Http404
from api.serializers import MyTokenObtainPairSerializer, RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView


from recipe.models import Recipe,Tag,UserHistory,UserFavourite
from recipe.features import get_similar_recipes_by_tags, search_recipes,create_or_add_to_history
from api.serializers import (
                            RecipeSerializer, 
                            RecipeCreateSerializer, 
                            RecipeUpdateSerializer,
                            UserSerializer,
                            )
from django.views.generic import TemplateView
from ipware import get_client_ip

User=get_user_model()


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class DocsView(TemplateView):
    template_name = 'api/docs.html'

@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/api/token/',
        '/api/register/',
        '/api/token/refresh/',
        '/api/test/'
        'recipes/', 
        'recipes/<slug:slug>',
    ]
    return Response(routes)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def testEndPoint(request):
    if request.method == 'GET':
        data = f"Congratulation {request.user}, your API just responded to GET request"
        return Response({'response': data}, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        try:
            body = request.body.decode('utf-8')
            data = json.loads(body)
            if 'text' not in data:
                return Response("Invalid JSON data", status.HTTP_400_BAD_REQUEST)
            text = data.get('text')
            data = f'Congratulation your API just responded to POST request with text: {text}'
            return Response({'response': data}, status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response("Invalid JSON data", status.HTTP_400_BAD_REQUEST)
    return Response("Invalid JSON data", status.HTTP_400_BAD_REQUEST)


class RecipeListAPIView(APIView):

    permission_classes = []

    def get(self, request):
        recipes = Recipe.objects.all()
        serializer = RecipeSerializer(recipes, many=True)
        return Response(serializer.data)

    def post(self, request):
        
        self.permission_classes = [IsAuthenticated]
        
        serializer = RecipeCreateSerializer(data=request.data)
        if serializer.is_valid():
            recipe = serializer.save(author=request.user)
            custom_tags = serializer.validated_data.get('custom_tags')
            if custom_tags:
                custom_tags = custom_tags.split(' ')
                for custom_tag in custom_tags:
                    tag, created = Tag.objects.get_or_create(name=custom_tag.strip())
                    recipe.tags.add(tag)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecipeDetailAPIView(APIView):

    permission_classes = []

    def get_object(self, slug):
        try:
            return Recipe.objects.get(slug=slug)
        except Recipe.DoesNotExist:
            raise Http404

    def get(self, request, slug):
        recipe = self.get_object(slug)
        create_or_add_to_history(request, recipe)
        serializer = RecipeSerializer(recipe)
        return Response(serializer.data)

    def put(self, request, slug):
        
        self.permission_classes = [IsAuthenticated]
        
        recipe = self.get_object(slug)
        if recipe.author != request.user:
            return Response({"error": "Privilege Error"}, status=status.HTTP_403_FORBIDDEN)

        serializer = RecipeUpdateSerializer(recipe, data=request.data)
        if serializer.is_valid():
            recipe = serializer.save()
            # custom_tags = serializer.validated_data.get('custom_tags')
            # if custom_tags:
            #     custom_tags = custom_tags.split(' ')
            #     for custom_tag in custom_tags:
            #         tag, created = Tag.objects.get_or_create(name=custom_tag.strip())
            #         recipe.tags.add(tag)
            return Response(serializer.data,status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def delete(self, request, slug):
        
        self.permission_classes = [IsAuthenticated]
        
        recipe = self.get_object(slug)
        if recipe.author != request.user:
            return Response({"error": "Privilege Error"}, status=status.HTTP_403_FORBIDDEN) 
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class RecipeSearchAPIView(APIView):
    
    def get(self, request):
        query = request.query_params.get('query', '')
        if query == '':
            return Response({"error": "No query"}, status=status.HTTP_400_BAD_REQUEST)
        recipes =search_recipes(query)
        serializer = RecipeSerializer(recipes, many=True)
        return Response(serializer.data)

class UserProfileAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            recipes = Recipe.objects.filter(author=user)
            #serialize the request user
            user= User.objects.get(username=user)
            user_serializer = UserSerializer(user)
            recipe_serializer = RecipeSerializer(recipes, many=True)
            return Response({
                        "userprofile":user_serializer.data,
                        "recipes":recipe_serializer.data
                        })
        except Exception as e:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
class UserHistoryAPIView(APIView):
    def get(self, request):
        try:
            if request.user.is_authenticated:
                user_history = UserHistory.objects.get(user=request.user)
            else:
                client_ip, is_routable = get_client_ip(request)
                user_history = UserHistory.objects.get(ip_address=client_ip)

            recipes = user_history.recipe.all()
            serializer = RecipeSerializer(recipes, many=True)

            return Response(serializer.data)
        except Exception as e:
            return Response([])