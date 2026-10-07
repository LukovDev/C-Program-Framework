//
// main.c - Основной файл программы.
//


// Подключаем:
#include <stdio.h>


// Точка входа в программу:
int main([[maybe_unused]] int argc, [[maybe_unused]] char *argv[]) {
    const char* hello = "Hello";
    printf("%s World!\n", hello);  // Hello World!
    return 0;
}
