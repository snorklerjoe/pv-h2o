//By Colin Holzman on Github: https://github.com/clnhlzmn/utils/tree/master/queue

/*
Copyright 2019 Colin Holzman
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

/**
\file queue.h
\brief A generic FIFO queue.
*/

#ifndef QUEUE_H
#define QUEUE_H

#include <stdlib.h>
#include <stdint.h>

/*
A very simple circular buffer.
Example:
QUEUE(test, int, count)
Creates:
struct queue_test {...};
static inline void queue_test_init(struct queue_test *) {...}
static inline int queue_test_push(struct queue_test *, int *) {...}
static inline int queue_test_pop(struct queue_test *, int *) {...}
API:
queue_*_init initializes a queue
queue_*_push pushes an item onto the queue, returns 0 if successful, not 0 if fail
queue_*_pop pops an item from the queue, returns 0 if successful, not 0 if fail
queue_*_foreach takes a function pointer and pointer to some context and for each
    element in the queue calls the function with a pointer to that element. If the
    returns zero queue_*_foreach will continue processing the rest of the items, if
    the function returns non zero then queue_*_foreach will not process any more items.
*/

/**
\brief Generates the queue api
\param name a name for the api with the given type and size
\param type the type of data to store in the queue
\param size the max number of data elements
*/
#define QUEUE(name, type, size)                                                         \
struct queue_##name {                                                                   \
    type storage[size];                                                                 \
    /*index of the read head, initialy 0*/                                              \
    size_t read;                                                                        \
    /*index of the write head, initialy 0*/                                             \
    size_t write;                                   \
    /*number of items in the queue*/                                                    \
    size_t count;                                                                       \
};                                                                                      \
static inline int queue_##name##_init(volatile struct queue_##name *self) {             \
    if (!self) return -1;                                                               \
    self->read = 0;                                                                     \
    self->write = 0;                                                                    \
    self->count = 0;                                                                    \
    return 0;                                                                           \
}                                                                                       \
static inline int queue_##name##_push(volatile struct queue_##name *self,               \
                                      const volatile type *item) {                      \
    if (!self || !item) return -1;                                                      \
    if (self->count < size) {                                                           \
        size_t next = (self->write + 1) % size;                                         \
        self->storage[next] = *item;                                                    \
        self->write = next;                                                             \
        self->count++;                                                                  \
        return 0;                                                                       \
    } else {                                                                            \
        return -1;                                                                      \
    }                                                                                   \
}                                                                                       \
static inline int queue_##name##_pop(volatile struct queue_##name *self,                \
                                     volatile type *item) {                             \
    if (!self || !item) return -1;                                                      \
    if (self->count > 0) {                                                              \
        size_t next = (self->read + 1) % size;                                          \
        *item = self->storage[next];                                                    \
        self->read = next;                                                              \
        self->count--;                                                                  \
        return 0;                                                                       \
    } else {                                                                            \
        return -1;                                                                      \
    }                                                                                   \
}                                                                                       \
static inline size_t queue_##name##_count(const volatile struct queue_##name *self) {   \
    if (!self) return 0;                                                                \
    return self->count;                                                                 \
}                                                                                       \
static inline void queue_##name##_foreach(volatile struct queue_##name *self,           \
                                          int (*fun)(volatile type *, volatile void *), \
                                          volatile void *ctx) {                         \
    if (!self) return;                                                                  \
    if (fun == NULL) return;                                                            \
    for (size_t i = 0; i < self->count; ++i) {                                          \
        if (fun(&self->storage[(self->read + i + 1) % size], ctx) != 0) break;          \
    }                                                                                   \
}\
\
static inline double queue_##name##_doublesum(volatile struct queue_##name *self) {                         \
    if (!self) return -1.0;                                                                  \
    double sum = 0.0;\
    for (size_t i = 0; i < size; ++i) {                                          \
        sum += self->storage[i];          \
    }                                                                                   \
    return sum;\
}

#endif