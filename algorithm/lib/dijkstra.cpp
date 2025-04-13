#include <iostream>
#include <cstdlib>
#include <string>
#include <stdio.h>

using namespace std;

struct edge {
  char *from;
  char *to;
  int dist;
};

struct node {
  int dist[10000];
};

extern "C" void test(struct node *graph, struct node *trace, int n_node){
  bool update[10000];
  for (int i=0; i < n_node; i++) update[i]=true;
  printf("haha\n");
  while(1){
    for(int cp=0; cp < n_node; cp++){
      update[cp]=false;
      for(int i=0; i < n_node; i++){
        if(update[i]) break;
        if(i == n_node-1) return;
      }
      for(int fp=0; fp < n_node; fp++){
        if((graph[cp].dist[fp] > -1) && update[fp]){
          for(int tp=0; tp < n_node; tp++){
            if(tp == cp) continue;
            if(graph[fp].dist[tp] > -1){
              if((graph[cp].dist[tp] == -1) || (graph[cp].dist[tp] > (graph[cp].dist[fp] + graph[fp].dist[tp]))){
                graph[cp].dist[tp]=graph[cp].dist[fp] + graph[fp].dist[tp];
                trace[cp].dist[tp]=trace[fp].dist[tp];
                update[cp]=true;
              }
            }
          }
        }
      }
    }
  }
}
