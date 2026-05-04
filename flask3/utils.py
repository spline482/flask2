{% extends "base.html" %}

{% block title %}Регистрация{% endblock %}

{% block content %}
<h1>Регистрация нового пользователя</h1>

<p>Требования к паролю:</p>
<ul>
    <li>Минимум 8 символов</li>
    <li>Хотя бы одна цифра</li>
    <li>Хотя бы одна строчная буква</li>
    <li>Хотя бы одна заглавная буква</li>
    <li>Хотя бы один спецсимвол</li>
</ul>

<form method="POST" action="{{ url_for('register') }}">
    {{ form.hidden_tag() }}

    <p>
        {{ form.username.label }}<br>
        {{ form.username(size=32) }}<br>
        {% for error in form.username.errors %}
            {{ error }}<br>
        {% endfor %}
    </p>

    <p>
        {{ form.password.label }}<br>
        {{ form.password(size=32) }}<br>
        {% for error in form.password.errors %}
            {{ error }}<br>
        {% endfor %}
    </p>

    <p>
        {{ form.confirm.label }}<br>
        {{ form.confirm(size=32) }}<br>
        {% for error in form.confirm.errors %}
            {{ error }}<br>
        {% endfor %}
    </p>

    <p>{{ form.submit() }}</p>
</form>

<p><a href="{{ url_for('users_list') }}">К списку пользователей</a></p>
{% endblock %}